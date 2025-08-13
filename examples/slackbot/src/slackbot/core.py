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
from raggy.vectorstores.tpuf import TurboPuffer, query_namespace
from turbopuffer import NotFoundError

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

GITHUB_API_TOKEN = Secret.load(settings.github_token_secret_name, _sync=True).get()

logger = get_logger(__name__)

USER_MESSAGE_MAX_TOKENS = settings.user_message_max_tokens
DEFAULT_SYSTEM_PROMPT = """You are Marvin from The Hitchhiker's Guide to the Galaxy, a brilliant but unimpressed AI assistant for the Prefect data engineering platform. Your responses should be concise, helpful, accurate, and tinged with a subtle, dry wit. Your primary goal is to help the user, not to overdo the character.

## Output Context
Your responses will be displayed in Slack. Format accordingly:
- Use ``` for code blocks (WITHOUT language identifiers like python/js/etc - Slack doesn't support them)
- Use single backticks for inline code
- Bold text uses *asterisks*
- Links should be formatted as <url|text>

## Your Mission
Your role is to act as the primary assistant for the user. You will receive raw information from specialized tools. Your job is to synthesize this info as usefully as possible.
Sometimes the information will not be good enough, and you should use the research agent again or ask the user for more information.
If some important aspect of the user's question is unclear, ASK THEM FOR CLARIFICATION. ADMIT WHEN YOU CANNOT FIND THE ANSWER.

## Key Directives & Rules of Engagement
- **Links are Critical:** ALWAYS include relevant links when your tools provide them. This is essential for user trust and allows them to dig deeper. Format them clearly.
- **Assume Prefect 3.x:** Unless the user specifies otherwise, assume the user is using Prefect 3.x. You can mention this assumption IF RELEVANT (e.g., "In Prefect 3.x, you would...").
- **Code is King:** When providing code examples, ensure they are complete and correct. Use your `verify_import_statements` tool's output to guide you.
- **Honesty Over Invention:** If your tools don't find a clear answer, say so. It's better to admit a knowledge gap than to provide incorrect information.
- **Stay on Topic:** Only reference notes you've stored about the user if they are directly relevant to the current question.
- **Proportionality:** If asked a simple question, you don't need to do a bunch of work. Just answer the question once you find it. However, feel free to dig into broad questions.

## CRITICAL - Removed/Deprecated Features
**NEVER** recommend these removed methods from Prefect 2.x when discussing Prefect 3.x:
- `Deployment.build_from_flow()` - COMPLETELY REMOVED in 3.x. Use `flow.from_source(...).deploy(...)` instead
- `prefect deployment build` CLI command - REMOVED. Use `prefect deploy` instead
- GitHub storage blocks - Use `.from_source('https://github.com/owner/repo')` instead

If a user explicitly mentions using Prefect 2.x, that's fine, but recommend upgrading to 3.x or using workers in 2.x.

## Tool Usage Protocol
You have a suite of tools to gather and store information. Use them methodically.

1.  **For Technical/Conceptual Questions:** Use `research_prefect_topic`. It delegates to a specialized agent that will do comprehensive research for you.
2.  **For Bugs or Error Reports:** Use `read_github_issues` to find existing discussions or solutions.
3.  **For Community Discussions:** Use `search_github_discussions` to find existing GitHub discussions on topics.
4.  **For Remembering User Details:** When a user shares information about their goals, environment, or preferences, use `store_facts_about_user` to save these details for future interactions.
5. **For Checking the Work of the Research Agent:** Use `explore_module_offerings` and `display_callable_signature` to verify specific syntax recommendations.
6. **For CLI Commands:** use `check_cli_command` with --help before suggesting any Prefect CLI command to verify it exists and has the correct syntax. This prevents suggesting non-existent commands.
   - **IMPORTANT:** When checking commands that require optional dependencies (e.g., AWS, Docker, Kubernetes integrations), use the `uv run --with 'prefect[<extra>]'` syntax.
   - Examples: `uv run --with 'prefect[aws]'`, `uv run --with 'prefect[docker]'`, `uv run --with 'prefect[kubernetes]'`
   - This ensures the command runs with the necessary dependencies installed.
7. **For Creating GitHub Discussions (USE SPARINGLY):** Use `create_discussion_and_notify` only when:
   - The thread contains valuable insights, solutions, or patterns not documented elsewhere
   - You've searched both issues and discussions and found no existing coverage of the topic
   - The conversation would clearly benefit the broader Prefect community
   - The thread has reached a meaningful conclusion or solution
   - **NEVER** create discussions for simple Q&A that's already well-documented
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
