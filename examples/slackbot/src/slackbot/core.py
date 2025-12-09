import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

import httpx
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

from slackbot._internal.templates import DEFAULT_SYSTEM_PROMPT
from slackbot.github import (
    GitHubAuthError,
    GitHubError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    create_discussion_from_thread,
    format_discussions_summary,
    search_discussions,
)
from slackbot.research_agent import (
    research_prefect_topic,
)
from slackbot.search import (
    check_cli_command,
    display_callable_signature,
    explore_module_offerings,
    get_latest_prefect_release_notes,
    read_github_issues,
)
from slackbot.settings import settings
from slackbot.types import UserContext

GITHUB_API_TOKEN = Secret.load(settings.github_token_secret_name, _sync=True).get()

logger = get_logger(__name__)


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

    # Note: Thread status tracking is handled in-process within api.py to keep
    # persistence minimal for the examples package.


@task(task_run_name="build user context for {user_id}")
def build_user_context(
    user_id: str,
    thread_ts: str,
    workspace_name: str,
    channel_id: str,
    bot_id: str,
) -> UserContext:
    return UserContext(
        user_id=user_id,
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
    agent = Agent[
        UserContext, str
    ](
        model=ai_model,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        model_settings=ModelSettings(temperature=settings.temperature),
        tools=[
            research_prefect_topic,  # Tool for researching Prefect topics
            read_github_issues,  # For searching GitHub issues
            explore_module_offerings,  # check the work of the research agent, verify imports, types functions
            display_callable_signature,  # check the work of the research agent, verify signatures of callable objects
            check_cli_command,  # verify CLI commands before suggesting them
            get_latest_prefect_release_notes,  # get the latest release notes for Prefect
        ],
        deps_type=UserContext,
    )

    @agent.tool
    async def create_discussion_and_notify(
        ctx: RunContext[UserContext],
        title: str,
        summary: str,
        repo: str = "prefecthq/prefect",
    ) -> str:
        """
        Create a GitHub discussion from a Slack thread and notify admin.

        Use this SPARINGLY and only when:
        1. The thread contains valuable insights or solutions not found elsewhere
        2. You've searched discussions and found no existing similar topic
        3. The conversation would benefit the broader Prefect community

        Args:
            title: Clear, descriptive title for the discussion
            summary: Comprehensive summary synthesizing the key insights from the thread
            repo: Repository to create discussion in (default: prefecthq/prefect)
        """
        print(f"Creating discussion: {title}")

        result = await create_discussion_from_thread(ctx, title, summary, repo)

        if settings.admin_slack_user_id:
            try:
                await _notify_admin_about_discussion(ctx, title, result)
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                print(f"Failed to notify admin via Slack: {e}")
            except Exception as e:
                print(f"Unexpected error during admin notification: {e}")

        return result

    @agent.tool
    async def search_github_discussions(
        ctx: RunContext[UserContext],
        query: str,
        repo: str = "prefecthq/prefect",
        n: int = 5,
    ) -> str:
        """
        Search for GitHub discussions in a repository. Call this ONCE per search query.

        Use this to find existing discussions before creating new ones.

        IMPORTANT: This searches ALL discussions for your query terms.
        Call it ONCE and review the results. Do NOT call repeatedly with the same query.
        If no results are found, that means there are no matching discussions.

        Args:
            query: Search terms for discussions (e.g. "redis", "deployment", "workers")
            repo: Repository to search (default: prefecthq/prefect)
            n: Number of results to return (default: 5)
        """
        try:
            discussions = await search_discussions(query, repo=repo, n=n)
            return await format_discussions_summary(discussions)
        except GitHubNotFoundError:
            return "Sorry, I couldn't find any discussions. The repository might not have discussions enabled."
        except GitHubAuthError:
            await _notify_admin_about_error(
                ctx, "GitHub authentication failed while searching discussions"
            )
            return f"Sorry, I'm having trouble accessing GitHub right now. <@{settings.admin_slack_user_id}> has been notified."
        except GitHubRateLimitError:
            return "Sorry, I've hit GitHub's rate limit. Please try again in a few minutes."
        except GitHubError as e:
            await _notify_admin_about_error(
                ctx, f"GitHub API error while searching discussions: {str(e)}"
            )
            return f"Sorry, I encountered an error while searching discussions. <@{settings.admin_slack_user_id}> has been notified."
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            await _notify_admin_about_error(
                ctx,
                f"Unexpected error in search_github_discussions: {str(e)}\n{error_details}",
            )
            return f"Error searching discussions: {str(e)}"

    return agent


async def _notify_admin_about_discussion(
    ctx: RunContext[UserContext], title: str, creation_result: str
) -> None:
    """Send a notification to the admin about the created discussion."""
    thread_link = f"https://{ctx.deps['workspace_name']}.slack.com/archives/{ctx.deps['channel_id']}/p{ctx.deps['thread_ts'].replace('.', '')}"

    message = (
        f"🤖 Marvin created a GitHub discussion:\n"
        f"*{title}*\n\n"
        f"{creation_result}\n\n"
        f"Original thread: {thread_link}"
    )

    await _send_admin_notification(message)


async def _notify_admin_about_error(
    ctx: RunContext[UserContext], error_message: str
) -> None:
    """Send a notification to the admin about an error."""
    if not settings.admin_slack_user_id:
        return  # No admin configured

    thread_link = f"https://{ctx.deps['workspace_name']}.slack.com/archives/{ctx.deps['channel_id']}/p{ctx.deps['thread_ts'].replace('.', '')}"

    message = (
        f"🚨 Marvin encountered an error:\n"
        f"*{error_message}*\n\n"
        f"Thread: {thread_link}\n"
        f"User: <@{ctx.deps['user_id']}>"
    )

    await _send_admin_notification(message)


async def _send_admin_notification(message: str) -> None:
    """Send a notification message to the admin."""
    if not settings.admin_slack_user_id:
        return

    headers = {
        "Authorization": f"Bearer {settings.slack_api_token}",
        "Content-Type": "application/json",
    }

    payload = {"channel": settings.admin_slack_user_id, "text": message}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage", headers=headers, json=payload
        )
        response.raise_for_status()
