import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

import httpx
from prefect import get_run_logger, task
from prefect.logging.loggers import get_logger
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models import KnownModelName, Model
from pydantic_ai.settings import ModelSettings
from raggy.vectorstores.tpuf import TurboPuffer
from turbopuffer import NotFoundError

from slackbot._internal.personalization import (
    PersonalizationSnapshot,
    load_personalization_snapshot,
)
from slackbot._internal.prompting import build_system_prompt
from slackbot._internal.templates import DEFAULT_SYSTEM_PROMPT
from slackbot._internal.tolerant_toolset import TolerantToolset
from slackbot._internal.vectors import select_rows_to_delete
from slackbot.assets import store_user_facts
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

logger = get_logger(__name__)


@dataclass
class Database:
    """Minimal async wrapper around a SQLite connection.

    Used by `_internal/thread_status.py` for cross-process dedup state
    (the `slack_thread_status` table). Thread message history lives in a
    `WritableFileSystem` block — see `_internal/message_store.py`.
    """

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
            return sqlite3.connect(str(file))

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


@task(task_run_name="build user context for {user_id}")
def build_user_context(
    user_id: str,
    user_question: str,
    thread_ts: str,
    workspace_name: str,
    channel_id: str,
    bot_id: str,
) -> UserContext:
    if user_id == "unknown":
        # no reliable human author this turn — don't read (or ever seed) a
        # shared user-facts-unknown namespace
        personalization = PersonalizationSnapshot(
            seen_before=False, profile_summary="", relevant_notes="", memory_warning=""
        )
    else:
        namespace = f"{settings.user_facts_namespace_prefix}{user_id}"
        personalization = load_personalization_snapshot(namespace, user_question)
    return UserContext(
        user_id=user_id,
        user_notes=personalization.relevant_notes,
        seen_before=personalization.seen_before,
        user_profile=personalization.profile_summary,
        memory_warning=personalization.memory_warning,
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
    ai_model = model or settings.bot_model
    slack_search_mcp = MCPServerStreamableHTTP(
        url="https://marvin-slack-thread-assets.fastmcp.app/mcp",
    )
    tolerant_slack_search = TolerantToolset(
        slack_search_mcp,
        on_error=lambda e: logger.warning(
            "slack-search MCP unavailable for this run: %s: %s",
            type(e).__name__,
            e,
        ),
    )
    agent = Agent[
        UserContext, str
    ](
        model=ai_model,
        model_settings=ModelSettings(temperature=settings.temperature),
        tools=[
            research_prefect_topic,  # Tool for researching Prefect topics
            read_github_issues,  # For searching GitHub issues
            explore_module_offerings,  # check the work of the research agent, verify imports, types functions
            display_callable_signature,  # check the work of the research agent, verify signatures of callable objects
            check_cli_command,  # verify CLI commands before suggesting them
            get_latest_prefect_release_notes,  # get the latest release notes for Prefect
        ],
        toolsets=[tolerant_slack_search],  # search Prefect community Slack threads
        deps_type=UserContext,
    )

    @agent.system_prompt
    def personality_and_maybe_notes(ctx: RunContext[UserContext]) -> str:
        system_prompt = build_system_prompt(DEFAULT_SYSTEM_PROMPT, ctx.deps)
        logger.debug("Built system prompt with contextual sections")
        return system_prompt

    @agent.tool
    async def store_facts_about_user(
        ctx: RunContext[UserContext], facts: list[str]
    ) -> str:
        """Store durable facts about the user for future conversations.

        Call this when the user shares context that will still be true next
        week — their environment (versions, cloud, infrastructure), goals, or
        preferences. Don't store thread-scoped debugging state ("flow X is
        currently stuck"); that belongs to this conversation only.

        Facts are deduplicated against near-identical existing facts at write
        time and timestamped, so restating known context is cheap but adds
        nothing.
        """
        user_id = ctx.deps["user_id"]
        if not user_id or user_id == "unknown" or user_id == ctx.deps["bot_id"]:
            logger.warning(
                "Refusing to store facts: no reliable human user (user_id=%s)",
                user_id,
            )
            return "Not storing facts: could not attribute them to a human user."
        logger.info("Storing %d facts about user %s", len(facts), user_id)
        # This creates an asset dependency: USER_FACTS depends on SLACK_MESSAGES
        message = await store_user_facts(ctx, facts)
        logger.info(message)
        return message

    @agent.tool
    def delete_facts_about_user(ctx: RunContext[UserContext], related_to: str) -> str:
        """Delete stored facts about the user related to a specific topic.

        Only facts semantically close to `related_to` are deleted; the
        response lists exactly what was removed so you can report it
        honestly. Use when the user asks you to forget something or when
        stored facts are clearly obsolete.
        """
        user_id = ctx.deps["user_id"]
        logger.info("Deleting facts about %s related to %r", user_id, related_to)
        with TurboPuffer(
            namespace=f"{settings.user_facts_namespace_prefix}{user_id}"
        ) as tpuf:
            try:
                rows = tpuf.query(related_to).rows or []
            except NotFoundError:
                return f"No facts are stored for user {user_id}."
            to_delete = select_rows_to_delete(rows)
            if not to_delete:
                return f"No stored facts matched {related_to!r}; nothing was deleted."
            tpuf.delete([row_id for row_id, _ in to_delete])
        deleted_lines = "\n".join(f"- {text}" for _, text in to_delete)
        logger.info("Deleted %d facts for user %s", len(to_delete), user_id)
        return (
            f"Deleted {len(to_delete)} facts related to {related_to!r}:\n"
            f"{deleted_lines}"
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

        Use this sparingly, and only when all of these hold:
        1. The thread contains valuable insights, solutions, or patterns not
           documented elsewhere
        2. You've searched both issues and discussions and found no existing
           coverage of the topic
        3. The conversation would clearly benefit the broader Prefect community
        4. The thread has reached a meaningful conclusion or solution

        Never create discussions for simple Q&A that's already well-documented.

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
