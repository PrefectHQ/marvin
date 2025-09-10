import asyncio
import re
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from prefect import Flow, State, flow, get_run_logger, task
from prefect.blocks.notifications import SlackWebhook
from prefect.cache_policies import NONE
from prefect.client.schemas.objects import FlowRun
from prefect.logging.loggers import get_logger
from prefect.states import Completed
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage

from slackbot._internal.constants import WORKSPACE_TO_CHANNEL_ID
from slackbot._internal.templates import CHANNEL_REDIRECT_MESSAGE, WELCOME_MESSAGE
from slackbot._internal.thread_status import (
    get_status as get_thread_status,
)
from slackbot._internal.thread_status import (
    mark_completed as mark_thread_completed,
)
from slackbot._internal.thread_status import (
    try_acquire as try_acquire_thread,
)
from slackbot.assets import summarize_thread
from slackbot.core import (
    Database,
    UserContext,
    build_user_context,
    create_agent,
)
from slackbot.settings import settings
from slackbot.slack import (
    SlackPayload,
    create_progress_message,
    get_channel_name,
    get_workspace_domain,
    post_slack_message,
)
from slackbot.strings import count_tokens, slice_tokens
from slackbot.wrap import WatchToolCalls, _progress_message, _tool_usage_counts

BOT_MENTION = r"<@(\w+)>"


logger = get_logger(__name__)

# Duplicate handling is coordinated via a small SQLite table in
# _internal.thread_status to work across processes.


def get_designated_channel_for_workspace(team_id: str) -> str | None:
    """Get the designated channel ID for a given workspace team ID."""
    return WORKSPACE_TO_CHANNEL_ID.get(team_id)


def check_if_designated_channel(channel_id: str, team_id: str) -> bool:
    """Check if the given channel is the designated channel for the workspace."""
    designated_channel = get_designated_channel_for_workspace(team_id)
    if not designated_channel:
        # If no designated channel is configured, allow all channels
        return True
    return channel_id == designated_channel


@task(name="run agent loop")
async def run_agent(
    cleaned_message: str,
    conversation: list[ModelMessage],
    user_context: UserContext,
    channel_id: str,
    thread_ts: str,
    decorator_settings: dict[str, Any] | None = None,
) -> AgentRunResult[str]:
    if decorator_settings is None:
        decorator_settings = {
            "cache_policy": NONE,
            "task_run_name": "execute {tool_name}",
            "log_prints": True,
        }

    start_time = time.monotonic()
    progress = await create_progress_message(
        channel_id=channel_id,
        thread_ts=thread_ts,
        initial_text="🔄 Thinking... this may take a while",
    )

    try:
        token = _progress_message.set(progress)
        # Initialize tool usage counts for this agent run
        counts_token = _tool_usage_counts.set(defaultdict(int))

        try:
            with WatchToolCalls(
                settings=decorator_settings,
                max_tool_calls=settings.max_tool_calls_per_turn,
            ):
                result = await create_agent(model=settings.model_name).run(
                    user_prompt=cleaned_message,
                    message_history=conversation,
                    deps=user_context,
                )
        finally:
            _progress_message.reset(token)
            _tool_usage_counts.reset(counts_token)

        await progress.update(
            f"✅ thought for {time.monotonic() - start_time:.1f} seconds"
        )
        return result
    except Exception as e:
        await progress.update(f"❌ Error: {str(e)}")
        raise


@flow(name="Handle Slack Message", retries=1)
async def handle_message(payload: SlackPayload, db: Database):
    logger = get_run_logger()
    event = payload.event
    if not event or not all([event.text, event.channel, (event.thread_ts or event.ts)]):
        logger.debug("Skipping invalid event")
        return Completed(message="Invalid event", name="SKIPPED")

    USER_MESSAGE_MAX_TOKENS = settings.user_message_max_tokens
    user_message = event.text or ""
    thread_ts = event.thread_ts or event.ts
    assert thread_ts is not None, "No thread_ts found"
    cleaned_message = re.sub(BOT_MENTION, "", user_message).strip()
    msg_len = count_tokens(cleaned_message)

    if msg_len > USER_MESSAGE_MAX_TOKENS:
        logger.warning(
            f"Message too long by {msg_len - USER_MESSAGE_MAX_TOKENS} tokens"
        )
        assert event.channel is not None, "No channel found"
        await post_slack_message(
            message=(
                "Your message was too long, here's your message at the allowed limit:"
                f"\n{slice_tokens(cleaned_message, USER_MESSAGE_MAX_TOKENS)}"
            ),
            channel_id=event.channel,
            thread_ts=thread_ts,
        )
        return Completed(message="Message too long", name="SKIPPED")

    if re.search(BOT_MENTION, user_message) and payload.authorizations:
        # Only gate the root message; replies should not be blocked
        is_root_message = event.thread_ts is None
        root_ts = thread_ts

        if is_root_message:
            # Cross-process acquire; only one handler should proceed for the root
            acquired = await try_acquire_thread(db, root_ts)
            if not acquired:
                status = await get_thread_status(db, root_ts)
                if status == "in_progress":
                    assert event.channel is not None, (
                        "Event channel is None when posting edit-ignored notice"
                    )
                    await post_slack_message(
                        message=(
                            "✋ I noticed you edited your original message. "
                            "I'm already working on your first version — please add any "
                            "clarifications as new messages in this thread so I don't lose track."
                        ),
                        channel_id=event.channel,
                        thread_ts=root_ts,
                    )
                    return Completed(
                        message="Ignored edit while in progress",
                        name="IGNORED_EDIT",
                        data=dict(thread_ts=root_ts),
                    )
                return Completed(
                    message="Duplicate root event after completion",
                    name="SKIPPED_DUPLICATE",
                    data=dict(thread_ts=root_ts),
                )

        # Check if this is the designated channel
        team_id = payload.team_id or ""
        is_designated = check_if_designated_channel(event.channel, team_id)

        if not is_designated:
            # Send redirect message to the designated channel
            designated_channel_id = get_designated_channel_for_workspace(team_id)
            if designated_channel_id:
                logger.info(
                    f"Redirecting user from {event.channel} to {designated_channel_id}"
                )
                await post_slack_message(
                    message=CHANNEL_REDIRECT_MESSAGE.format(
                        channel_id=designated_channel_id
                    ),
                    channel_id=event.channel,
                    thread_ts=thread_ts,
                )
                return Completed(
                    message="Redirected to designated channel",
                    name="REDIRECTED",
                    data=dict(
                        from_channel=event.channel,
                        to_channel=designated_channel_id,
                    ),
                )

        logger.info(
            f"Processing message in thread {thread_ts}\nUser message: {cleaned_message}"
        )
        conversation = await db.get_thread_messages(thread_ts)

        bot_user_id = None
        if payload.authorizations:
            bot_auth = next(
                (auth for auth in payload.authorizations or [] if auth.is_bot), None
            )
            if bot_auth:
                bot_user_id = bot_auth.user_id

        user_context = build_user_context(
            user_id=event.user,
            user_question=cleaned_message,
            thread_ts=thread_ts,
            workspace_name=await get_workspace_domain(),
            channel_id=event.channel or "unknown",
            bot_id=bot_user_id or "unknown",
        )

        try:
            result = await run_agent(
                cleaned_message,
                conversation,
                user_context,
                event.channel,
                thread_ts,
            )  # type: ignore

            await db.add_thread_messages(thread_ts, result.new_messages())
            conversation.extend(result.new_messages())
            assert event.channel is not None, "No channel found"
            await task(post_slack_message)(
                message=result.output,
                channel_id=event.channel,
                thread_ts=thread_ts,
            )
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            assert event.channel is not None, "No channel found"
            await task(post_slack_message)(
                message="Sorry, I encountered an error while processing your request. Please try again.",
                channel_id=event.channel,
                thread_ts=thread_ts,
            )
            # Still return completed so we don't retry
            return Completed(
                message="Error during agent execution",
                name="ERROR_HANDLED",
                data=dict(error=str(e), user_context=user_context),
            )
        finally:
            # Only mark completion for the root message; do not block replies
            if "is_root_message" in locals() and is_root_message:
                try:
                    await mark_thread_completed(db, root_ts)
                except Exception:
                    logger.warning("Failed to mark thread as completed")

        return Completed(
            message="Responded to mention",
            data=dict(user_context=user_context, conversation=conversation),
        )

    return Completed(message="Skipping non-mention", name="SKIPPED")


@handle_message.on_completion
async def summarize_thread_so_far(flow: Flow, flow_run: FlowRun, state: State[Any]):
    result = await state.result()

    # Skip summarization for redirects and other non-conversation states
    if not isinstance(result, dict) or "conversation" not in result:
        return

    conversation = result["conversation"]

    if len(conversation) % 4 != 0:  # only summarize thread every 4 messages
        return

    await summarize_thread(result["user_context"], conversation)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with Database.connect(settings.db_file) as db:
        app.state.db = db
        yield


app = FastAPI(lifespan=lifespan)


@app.post("/chat")
async def chat_endpoint(request: Request) -> dict[str, Any]:
    try:
        payload = SlackPayload.model_validate(await request.json())
    except Exception as e:
        logger.error(f"Error parsing Slack payload: {e}")
        slack_webhook = await SlackWebhook.load("marvin-bot-pager")
        await slack_webhook.notify(
            body=f"Error parsing Slack payload: {e}",
            subject="Slackbot Error",
        )
        raise HTTPException(400, "Invalid event type")

    db: Database = request.app.state.db

    if payload.type == "event_callback":
        if not payload.event:
            raise HTTPException(400, "No event found")

        if payload.event.type == "team_join":
            logger.info(f"New team member joined: {payload.event.user}")
            user_id = payload.event.user
            assert isinstance(user_id, str), "expected user_id to be a string"

            await post_slack_message(
                WELCOME_MESSAGE.format(user_id=user_id),
                channel_id=user_id,
            )
        else:
            if not payload.event.channel:
                raise HTTPException(400, "No channel found")

            channel_name = await get_channel_name(payload.event.channel)
            if channel_name.startswith("D"):
                logger.warning(f"Attempted DM in channel: {channel_name}")
                slack_webhook = await SlackWebhook.load("marvin-bot-pager")
                await slack_webhook.notify(
                    body=f"Attempted DM: {channel_name}",
                    subject="Slackbot DM Warning",
                )
                return {"status": "skipped dm"}

            logger.info(f"Processing message in {channel_name}")
            ts = payload.event.thread_ts or payload.event.ts
            flow_opts: dict[str, Any] = dict(
                flow_run_name=f"respond in {channel_name}/{ts}",
            )

            asyncio.create_task(handle_message.with_options(**flow_opts)(payload, db))
    elif payload.type == "url_verification":
        return {"challenge": payload.challenge}
    else:
        raise HTTPException(400, "Invalid event type")

    return {"status": "ok"}
