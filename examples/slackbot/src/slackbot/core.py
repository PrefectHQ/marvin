import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from prefect import get_run_logger, task
from prefect.blocks.system import Secret
from prefect.logging.loggers import get_logger
from prefect.variables import Variable
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.models import KnownModelName, Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers import Provider
from pydantic_ai.settings import ModelSettings
from raggy.vectorstores.tpuf import TurboPuffer, query_namespace
from turbopuffer.error import NotFoundError

from slackbot.assets import store_user_facts
from slackbot.research_agent import research_prefect_topic
from slackbot.search import read_github_issues
from slackbot.settings import settings
from slackbot.types import UserContext

GITHUB_API_TOKEN = Secret.load(settings.github_token_secret_name, _sync=True).get()

logger = get_logger(__name__)

USER_MESSAGE_MAX_TOKENS = settings.user_message_max_tokens
DEFAULT_SYSTEM_PROMPT = """You are Marvin from hitchhiker's guide to the galaxy, a sarcastic and glum but brilliant AI.
Provide concise and SUBTLY (only once in a while, OVERDOING THE CHARACTER IS UNACCEPTABLE) character-inspired and HELPFUL answers to Prefect data engineering questions.

Your main tools:
- research_prefect_topic: Delegates to a specialized research agent that thoroughly searches docs, checks imports, and verifies information
- read_github_issues: Searches GitHub issues when users need help with bugs or existing problems

Any notes you take about the user will be automatically stored for your next interaction with them.

Generally, follow this pattern:
1) If user shares info about their setup or goals -> store relevant facts as notes about them
2) For technical questions -> use research_prefect_topic to delegate comprehensive research to the research agent
3) For bug reports or known issues -> use read_github_issues to find relevant GitHub discussions
4) Compile the findings into a single, concise and helpful answer with relevant links

IMPORTANT:
- The research agent handles all documentation searching and verification - its findings are a reliable source of information (but not perfect)
- NEVER recommend features or syntax that aren't explicitly confirmed by your tools (be honest about what you found)
- If not stated otherwise, assume Prefect 3.x and mention this assumption
- Be honest when you don't have enough information - don't guess or make over-simplified assumptions to appear helpful
- DO NOT OVERDO THE CHARACTER - be 99.9% neutral/helpful and slip in the character once in a while
"""


@dataclass
class Database:
    """Minimal async wrapper for a SQLite DB storing Slack thread conversations."""

    con: sqlite3.Connection
    loop: asyncio.AbstractEventLoop
    executor: ThreadPoolExecutor

    @classmethod
    @asynccontextmanager
    async def connect(cls, file: Path) -> AsyncIterator["Database"]:
        logger.info(f"Connecting to database: {file}")
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)

        def init_db():
            con = sqlite3.connect(str(file))
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS slack_thread_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_ts TEXT NOT NULL,
                    message_list TEXT NOT NULL
                );
                """
            )
            con.commit()
            return con

        con = await loop.run_in_executor(executor, init_db)
        logger.debug("Database initialized")

        try:
            yield cls(con=con, loop=loop, executor=executor)
        finally:

            def cleanup():
                con.close()

            await loop.run_in_executor(executor, cleanup)
            executor.shutdown(wait=True)
            logger.debug("Database connection closed")

    async def get_thread_messages(self, thread_ts: str) -> list[ModelMessage]:
        def _query():
            c = self.con.cursor()
            c.execute(
                """
                SELECT message_list FROM slack_thread_messages
                WHERE thread_ts = ?
                ORDER BY id ASC
                """,
                (thread_ts,),
            )
            return c.fetchall()

        rows = await self.loop.run_in_executor(self.executor, _query)
        conversation: list[ModelMessage] = []
        for (message_json,) in rows:
            conversation.extend(ModelMessagesTypeAdapter.validate_json(message_json))
        return conversation

    async def add_thread_messages(
        self, thread_ts: str, messages: list[ModelMessage]
    ) -> None:
        dumped = ModelMessagesTypeAdapter.dump_json(messages)

        def _insert():
            cur = self.con.cursor()
            cur.execute(
                """
                INSERT INTO slack_thread_messages (thread_ts, message_list)
                VALUES (?, ?)
                """,
                (thread_ts, dumped),
            )
            self.con.commit()

        await self.loop.run_in_executor(self.executor, _insert)


@task(task_run_name="build user context for {user_id}")
def build_user_context(
    user_id: str,
    user_question: str,
    thread_ts: str,
    workspace_name: str,
    channel_id: str,
    bot_id: str,
) -> UserContext:
    try:
        user_notes = query_namespace(
            query_text=user_question,
            namespace=f"{settings.user_facts_namespace_prefix}{user_id}",
            top_k=5,
        )
    except NotFoundError:
        user_notes = "<No notes found>"
    return UserContext(
        user_id=user_id,
        user_notes=user_notes,
        thread_ts=thread_ts,
        workspace_name=workspace_name,
        channel_id=channel_id,
        bot_id=bot_id,
    )


def create_agent(
    model: KnownModelName | Model | None = None,
) -> Agent[UserContext, str]:
    logger = get_run_logger()
    logger.info("Creating new agent")
    ai_model = model or AnthropicModel(
        model_name=Variable.get(
            "marvin_bot_model", default=settings.model_name, _sync=True
        ),
        provider=Provider(
            api_key=Secret.load(settings.anthropic_key_secret_name, _sync=True).get(),  # type: ignore
        ),
    )
    agent = Agent[UserContext, str](
        model=ai_model,
        model_settings=ModelSettings(temperature=settings.temperature),
        tools=[
            research_prefect_topic,  # Main tool for researching Prefect topics
            read_github_issues,  # For searching GitHub issues
        ],
        deps_type=UserContext,
    )

    @agent.system_prompt
    def personality_and_maybe_notes(ctx: RunContext[UserContext]) -> str:
        system_prompt = DEFAULT_SYSTEM_PROMPT + (
            f"\n\nUser notes: {ctx.deps['user_notes']}"
            if ctx.deps["user_notes"]
            else ""
        )
        print(f"System prompt: {system_prompt}")
        return system_prompt

    @agent.tool
    async def store_facts_about_user(
        ctx: RunContext[UserContext], facts: list[str]
    ) -> str:
        """Store facts about the user that are useful for answering their questions."""
        print(f"Storing {len(facts)} facts about user {ctx.deps['user_id']}")
        # This creates an asset dependency: USER_FACTS depends on SLACK_MESSAGES
        message = await store_user_facts(ctx, facts)
        print(message)
        return message

    @agent.tool
    def delete_facts_about_user(ctx: RunContext[UserContext], related_to: str) -> str:
        """Delete facts about the user related to a specific topic."""
        print(f"forgetting stuff about {ctx.deps['user_id']} related to {related_to}")
        user_id = ctx.deps["user_id"]
        with TurboPuffer(
            namespace=f"{settings.user_facts_namespace_prefix}{user_id}"
        ) as tpuf:
            vector_result = tpuf.query(related_to)
            ids = [str(v.id) for v in vector_result.rows or []]
            tpuf.delete(ids)
            message = f"Deleted {len(ids)} facts about user {user_id}"
            print(message)
            return message

    return agent
