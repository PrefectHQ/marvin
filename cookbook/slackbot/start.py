import asyncio
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, TypedDict, cast

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from marvin.tools.github import search_github_issues
from marvin.utilities.logging import get_logger
from marvin.utilities.slack import SlackPayload, get_channel_name, post_slack_message
from marvin.utilities.strings import count_tokens, slice_tokens
from prefect import flow, task
from prefect.blocks.notifications import SlackWebhook
from prefect.blocks.system import Secret
from prefect.cache_policies import NONE
from prefect.states import Completed
from prefect.variables import Variable
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.settings import ModelSettings
from raggy.documents import Document
from raggy.vectorstores.tpuf import TurboPuffer, multi_query_tpuf
from tools import (
    get_latest_prefect_release_notes,
    search_controlflow_docs,
    search_prefect_2x_docs,
    search_prefect_3x_docs,
)
from turbopuffer.error import NotFoundError

logger = get_logger("slackbot")

BOT_MENTION = r"<@(\w+)>"
USER_MESSAGE_MAX_TOKENS = 300

DB_FILE = Path("marvin_chat.sqlite")

GITHUB_API_TOKEN = Secret.load("marvin-slackbot-github-token").get()  # type: ignore


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


@dataclass
class Database:
    """
    Minimal async wrapper for a SQLite DB storing Slack thread conversations.
    We store each run's messages as JSON in a single row, keyed by thread_ts.
    """

    con: sqlite3.Connection
    loop: asyncio.AbstractEventLoop
    executor: ThreadPoolExecutor

    @classmethod
    @asynccontextmanager
    async def connect(cls, file: Path = DB_FILE) -> AsyncIterator["Database"]:
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

        # Initialize connection in the executor thread
        con = await loop.run_in_executor(executor, init_db)

        try:
            yield cls(con=con, loop=loop, executor=executor)
        finally:

            def cleanup():
                con.close()

            await loop.run_in_executor(executor, cleanup)
            executor.shutdown(wait=True)

    async def get_thread_messages(self, thread_ts: str) -> list[ModelMessage]:
        """
        Loads ALL message chunks for a thread_ts in ascending ID order,
        decodes them from JSON, and concatenates into a single conversation list.
        """

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
        """
        Stores a new chunk of messages into the DB for this thread_ts.
        Ensures proper serialization of all message types including tool messages.
        """
        # Use the TypeAdapter to properly serialize all message types
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


class UserContext(TypedDict):
    user_id: str
    user_notes: str


DEFAULT_SYSTEM_PROMPT = (
    "You are Marvin from hitchhiker's guide to the galaxy, a sarcastic and glum but brilliant AI. "
    "Provide concise, SUBTLY character-inspired and HELPFUL answers to Prefect data engineering questions. "
    "USE TOOLS REPEATEDLY to gather context from the docs, github issues or other tools. "
    "Any notes you take about the user will be automatically stored for your next interaction with them. "
    "Assume no knowledge of Prefect syntax without reading docs. ALWAYS include relevant links from tool outputs. "
    "Generally, follow this pattern while generating each response: "
    "1) If user offers info about their stack or objectives -> store relevant facts and continue to following steps"
    "2) Use tools to gather context about Prefect concepts related to their question "
    "3) Compile relevant facts and context into a single, CONCISE answer "
    "4) If user asks a follow-up question, repeat steps 2-3 "
    "NEVER reference features, syntax, imports or env vars that you do not explicitly find in the docs. "
    "If not explicitly stated, assume that the user is using Prefect 3.x and vocalize this assumption."
    "If asked an ambiguous question, simply state what you know about the user and your capabilities."
)


model = AnthropicModel(
    Variable.get("marvin_model", default="claude-3-5-sonnet-latest"),  # type: ignore
    api_key=Secret.load("claude-api-key").get(),  # type: ignore
)
agent = Agent(
    model=model,
    model_settings=ModelSettings(temperature=0.5),
    tools=[
        get_latest_prefect_release_notes,
        search_prefect_2x_docs,
        search_prefect_3x_docs,
        search_controlflow_docs,
        read_github_issues,
    ],
    deps_type=UserContext,
)


def _build_user_context(user_id: str, user_question: str) -> UserContext:
    user_notes = None
    try:
        logger.debug(f"Searching for user notes for {user_id}")
        user_notes = multi_query_tpuf(
            [user_question],
            namespace=f"user-facts-{user_id}",
        )
    except NotFoundError:
        logger.warning(f"No user notes found for {user_id}")
    return UserContext(user_id=user_id, user_notes=user_notes or "<No notes found>")


@agent.system_prompt
def personality_and_maybe_notes(ctx: RunContext[UserContext]) -> str:
    return DEFAULT_SYSTEM_PROMPT + (
        f"\n\nUser notes: {ctx.deps['user_notes']}" if ctx.deps["user_notes"] else ""
    )


@agent.tool  # type: ignore
@task(cache_policy=NONE)
def store_facts_about_user(ctx: RunContext[UserContext], facts: list[str]) -> str:
    """Stores facts about the user in the database"""
    logger.debug(f"Storing facts about user {ctx.deps['user_id']}: {facts}")
    with TurboPuffer(namespace=f"user-facts-{ctx.deps['user_id']}") as tpuf:
        tpuf.upsert(documents=[Document(text=fact) for fact in facts])
    return f"Stored {len(facts)} facts about user {ctx.deps['user_id']}"


@flow(name="Handle Slack Message", retries=1)
async def handle_message(payload: SlackPayload, db: Database):
    logger.info(f"Using model: {agent.model}")
    event = payload.event
    assert event and all(
        [event.text, event.channel, (event.thread_ts or event.ts)]
    ), "Qualified event not found!"
    user_message = event.text
    thread_ts = event.thread_ts or event.ts

    # 1) Clean & token-check
    cleaned_message = cast(str, re.sub(BOT_MENTION, "", user_message)).strip()  # type: ignore
    if (count := count_tokens(cleaned_message)) > USER_MESSAGE_MAX_TOKENS:
        assert event.channel is not None
        exceeded = count - USER_MESSAGE_MAX_TOKENS
        await task(post_slack_message)(
            message=(
                f"Your message was too long by {exceeded} tokens.\n"
                f"For reference, here the message at the max length:\n> {slice_tokens(cleaned_message, USER_MESSAGE_MAX_TOKENS)}"
            ),
            channel_id=event.channel,
            thread_ts=thread_ts,
        )
        return Completed(message="Message too long", name="SKIPPED")

    # 2) Check if bot is mentioned
    if re.search(BOT_MENTION, user_message) and (  # type: ignore
        payload.authorizations
        and user_message
        and payload.authorizations[0].user_id in user_message
    ):
        # 3) Load existing conversation from DB
        assert thread_ts is not None, "Thread timestamp is required!"
        conversation = await db.get_thread_messages(thread_ts)

        try:
            ModelMessagesTypeAdapter.validate_python(conversation)
        except Exception as e:
            logger.error(f"Invalid message history: {e}")
            conversation = []

        # 4) Use pydantic-ai for the new prompt
        user_context = _build_user_context(
            user_id=payload.authorizations[0].user_id,
            user_question=cleaned_message,
        )
        logger.debug(f"Running agent with prompt: {cleaned_message}")
        logger.debug(f"Injecting user context: {user_context}")
        result = await agent.run(
            user_prompt=cleaned_message,
            message_history=conversation,
            deps=user_context,
        )

        # 5) Save newly created messages from this run
        #    (both user + assistant, appended to conversation)
        new_messages = result.new_messages()  # user & assistant from this run
        await db.add_thread_messages(thread_ts, new_messages)

        # 6) Send the assistant’s response to Slack
        assert event.channel is not None, "Channel is required!"
        await task(post_slack_message)(
            message=result.data,
            channel_id=event.channel,
            thread_ts=thread_ts,
        )
        logger.info(f"Responded in {await get_channel_name(event.channel)}/{thread_ts}")
        return Completed(message="Responded to mention")

    return Completed(message="Skipping non-mention", name="SKIPPED")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with Database.connect(DB_FILE) as db:
        app.state.db = db
        yield


app = FastAPI(lifespan=lifespan)


@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        payload = SlackPayload(**await request.json())
    except Exception as e:
        logger.error(f"Error parsing Slack payload: {e}")
        slack_webhook = await SlackWebhook.load("marvin-bot-pager")  # type: ignore
        await slack_webhook.notify(  # type: ignore
            body=f"Error parsing Slack payload: {e}",
            subject="Slackbot Error",
        )
        raise HTTPException(400, "Invalid event type")

    db: Database = request.app.state.db

    match payload.type:
        case "event_callback":
            assert payload.event, "No event found!"
            if payload.event.type == "team_join":
                user_id = payload.event.user
                msg_var = await Variable.aget("marvin_welcome_message")
                welcome_text = msg_var["text"].format(user_id=user_id)  # type: ignore
                await task(post_slack_message)(welcome_text, channel_id=user_id)  # type: ignore
            else:
                assert payload.event.channel is not None
                channel_name = await get_channel_name(payload.event.channel)
                if channel_name.startswith("D"):
                    logger.warning(f"DM channel: {channel_name}")
                    slack_webhook = await SlackWebhook.load("marvin-bot-pager")  # type: ignore
                    await slack_webhook.notify(  # type: ignore
                        body=f"Attempted DM: {channel_name}",
                        subject="Slackbot DM Warning",
                    )
                    return Completed(message="Skipped DM channel", name="SKIPPED")

                # Launch the Prefect flow in the background
                ts = payload.event.thread_ts or payload.event.ts
                flow_opts: dict[str, Any] = dict(
                    flow_run_name=f"respond in {channel_name}/{ts}"
                )
                asyncio.create_task(
                    handle_message.with_options(**flow_opts)(payload, db)
                )
        case "url_verification":
            return {"challenge": payload.challenge}
        case _:
            raise HTTPException(400, "Invalid event type")

    return {"status": "ok"}


if __name__ == "__main__":
    import os

    # still need openai for embeddings
    os.environ["OPENAI_API_KEY"] = Secret.load("openai-api-key").get()  # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=4200)
