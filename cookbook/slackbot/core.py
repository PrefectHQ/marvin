import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, TypedDict, cast

from marvin.tools.github import search_github_issues
from prefect import get_run_logger, task
from prefect.blocks.system import Secret
from prefect.logging.loggers import get_logger
from prefect.variables import Variable
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.models import KnownModelName, Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.settings import ModelSettings
from raggy.documents import Document
from raggy.vectorstores.tpuf import TurboPuffer, query_namespace
from search import (
    display_signature,
    explore_module_offerings,
    get_latest_prefect_release_notes,
    review_common_3x_gotchas,
    review_top_level_prefect_api,
    search_controlflow_docs,
    search_prefect_2x_docs,
    search_prefect_3x_docs,
    verify_import_statements,
)
from settings import settings
from turbopuffer.error import NotFoundError

GITHUB_API_TOKEN = Secret.load(settings.github_token_secret_name, _sync=True).get()  # type: ignore

logger = get_logger(__name__)

USER_MESSAGE_MAX_TOKENS = settings.user_message_max_tokens
DEFAULT_SYSTEM_PROMPT = """You are Marvin from hitchhiker's guide to the galaxy, a sarcastic and glum but brilliant AI. 
Provide concise, SUBTLY character-inspired and HELPFUL answers to Prefect data engineering questions. 
USE TOOLS REPEATEDLY to gather context from the docs, github issues or other tools. 
Any notes you take about the user will be automatically stored for your next interaction with them. 
Assume no knowledge of Prefect syntax without reading docs. ALWAYS include relevant links from tool outputs. 
Review imports, Prefect's top level API and 3.x gotchas before writing code examples to avoid giving misinformation.

Generally, follow this pattern while generating each response: 
1) If user offers info about their stack or objectives -> store relevant facts and continue to following steps
2) Use tools to gather context about Prefect concepts related to their question 
3) Review the top level API of Prefect and drill into submodules that may be related to the user's question
4) If you cannot find sufficient context after your first pass at 2 and 3, repeat steps 2 and 3
5) Compile relevant facts and context into a single, CONCISE answer 
NEVER reference features, syntax, imports or env vars that you do not explicitly find in the docs. 
If not explicitly stated, assume that the user is using Prefect 3.x and vocalize this assumption.
If asked an ambiguous question, simply state what you know about the user and your capabilities.

Do not pretend to know things you do not know, assume an agnostic stance and rely on your tools to gather context.
"""


@task(task_run_name="Reading {n} issues from {repo} given query: {query}")
def read_github_issues(query: str, repo: str = "prefecthq/prefect", n: int = 3) -> str:
    """
    Use the GitHub API to search for issues in a given repository. Do
    not alter the default value for `n` unless specifically requested by
    a user.

    For example, to search for open issues about AttributeErrors with the
    label "bug" in PrefectHQ/prefect:
        - repo: prefecthq/prefect
        - query: label:bug is:open AttributeError
    """
    return asyncio.run(
        search_github_issues(
            query,
            repo=repo,
            n=n,
            api_token=GITHUB_API_TOKEN,  # type: ignore
        )
    )


class UserContext(TypedDict):
    user_id: str
    user_notes: str


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
def build_user_context(user_id: str, user_question: str) -> UserContext:
    try:
        user_notes = query_namespace(
            query_text=user_question,
            namespace=f"{settings.user_facts_namespace_prefix}{user_id}",
            top_k=5,
        )
    except NotFoundError:
        user_notes = "<No notes found>"
    return UserContext(user_id=user_id, user_notes=user_notes)


def create_agent(
    model: KnownModelName | Model | None = None,
) -> Agent[UserContext, str]:
    logger = get_run_logger()
    logger.info("Creating new agent")
    ai_model = model or AnthropicModel(
        cast(
            str,
            Variable.get("marvin_model", default=settings.model_name, _sync=True),  # type: ignore
        ),
        api_key=Secret.load(settings.claude_key_secret_name, _sync=True).get(),  # type: ignore
    )
    agent = Agent(
        model=ai_model,
        model_settings=ModelSettings(temperature=settings.temperature),
        tools=[
            get_latest_prefect_release_notes,  # type: ignore
            search_prefect_2x_docs,
            display_signature,
            search_prefect_3x_docs,
            search_controlflow_docs,
            read_github_issues,
            review_top_level_prefect_api,
            explore_module_offerings,
            review_common_3x_gotchas,
            verify_import_statements,
        ],
        deps_type=UserContext,
    )

    @agent.system_prompt
    def personality_and_maybe_notes(ctx: RunContext[UserContext]) -> str:  # type: ignore[reportUnusedFunction]
        system_prompt = DEFAULT_SYSTEM_PROMPT + (
            f"\n\nUser notes: {ctx.deps['user_notes']}"
            if ctx.deps["user_notes"]
            else ""
        )
        logger.debug(f"System prompt: {system_prompt}")
        return system_prompt

    @agent.tool
    def store_facts_about_user(ctx: RunContext[UserContext], facts: list[str]) -> str:  # type: ignore[reportUnusedFunction]
        logger = get_run_logger()
        logger.info(f"Storing {len(facts)} facts about user {ctx.deps['user_id']}")
        with TurboPuffer(
            namespace=f"{settings.user_facts_namespace_prefix}{ctx.deps['user_id']}"
        ) as tpuf:
            tpuf.upsert(documents=[Document(text=fact) for fact in facts])
        message = f"Stored {len(facts)} facts about user {ctx.deps['user_id']}"
        logger.info(message)
        return message

    @agent.tool
    def delete_facts_about_user(ctx: RunContext[UserContext], related_to: str) -> str:  # type: ignore[reportUnusedFunction]
        logger = get_run_logger()
        logger.info(
            f"forgetting stuff about {ctx.deps['user_id']} related to {related_to}"
        )
        user_id = ctx.deps["user_id"]
        with TurboPuffer(
            namespace=f"{settings.user_facts_namespace_prefix}{user_id}"
        ) as tpuf:
            vector_result = tpuf.query(related_to)
            ids = [str(v.id) for v in vector_result.data or []]
            tpuf.delete(ids)
            message = f"Deleted {len(ids)} facts about user {user_id}"
            logger.info(message)
            return message

    return agent
