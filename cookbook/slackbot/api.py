import asyncio
import re
from contextlib import asynccontextmanager
from typing import Any

from core import (
    USER_MESSAGE_MAX_TOKENS,
    Database,
    build_user_context,
    create_agent,
)
from fastapi import FastAPI, HTTPException, Request
from marvin.utilities.logging import get_logger
from marvin.utilities.slack import SlackPayload, get_channel_name, post_slack_message
from marvin.utilities.strings import count_tokens
from prefect import flow, task
from prefect.blocks.notifications import SlackWebhook
from prefect.states import Completed
from prefect.variables import Variable
from settings import settings

BOT_MENTION = r"<@(\w+)>"

agent = create_agent()

logger = get_logger(__name__)


@flow(name="Handle Slack Message", retries=1)
async def handle_message(payload: SlackPayload, db: Database):
    event = payload.event
    if not event or not all([event.text, event.channel, (event.thread_ts or event.ts)]):
        logger.debug("Skipping invalid event")
        return Completed(message="Invalid event", name="SKIPPED")

    user_message = event.text or ""
    thread_ts = event.thread_ts or event.ts
    assert thread_ts is not None
    cleaned_message = re.sub(BOT_MENTION, "", user_message).strip()

    if (count := count_tokens(cleaned_message)) > USER_MESSAGE_MAX_TOKENS:
        logger.warning(f"Message too long by {count - USER_MESSAGE_MAX_TOKENS} tokens")
        exceeded = count - USER_MESSAGE_MAX_TOKENS
        assert event.channel is not None, "No channel found"
        await post_slack_message(
            message=f"Your message was too long by {exceeded} tokens...",
            channel_id=event.channel,
            thread_ts=thread_ts,
        )
        return Completed(message="Message too long", name="SKIPPED")

    if re.search(BOT_MENTION, user_message) and payload.authorizations:
        logger.info(f"Processing message in thread {thread_ts}")
        conversation = await db.get_thread_messages(thread_ts)

        user_context = build_user_context(
            user_id=payload.authorizations[0].user_id,
            user_question=cleaned_message,
        )

        result = await task(agent.run)(
            user_prompt=cleaned_message,
            message_history=conversation,
            deps=user_context,
        )
        await db.add_thread_messages(thread_ts, result.new_messages())
        assert event.channel is not None, "No channel found"
        await task(post_slack_message)(
            message=result.data,
            channel_id=event.channel,
            thread_ts=thread_ts,
        )
        return Completed(message="Responded to mention")

    return Completed(message="Skipping non-mention", name="SKIPPED")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with Database.connect(settings.db_file) as db:
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

    if payload.type == "event_callback":
        if not payload.event:
            raise HTTPException(400, "No event found")

        if payload.event.type == "team_join":
            logger.info(f"New team member joined: {payload.event.user}")
            user_id = payload.event.user
            assert isinstance(user_id, str), "expected user_id to be a string"
            message_variable = await Variable.aget("marvin_welcome_message")
            message_text = message_variable.value["text"]  # type: ignore
            assert isinstance(message_text, str), "expected message_text to be a string"
            welcome_text = message_text.format(user_id=user_id)
            await post_slack_message(
                welcome_text,
                channel_id=user_id,
            )
        else:
            if not payload.event.channel:
                raise HTTPException(400, "No channel found")

            channel_name = await get_channel_name(payload.event.channel)
            if channel_name.startswith("D"):
                logger.warning(f"Attempted DM in channel: {channel_name}")
                slack_webhook = await SlackWebhook.load("marvin-bot-pager")  # type: ignore
                await slack_webhook.notify(  # type: ignore
                    body=f"Attempted DM: {channel_name}",
                    subject="Slackbot DM Warning",
                )
                return {"status": "skipped dm"}

            logger.info(f"Processing message in {channel_name}")
            ts = payload.event.thread_ts or payload.event.ts
            flow_opts: dict[str, Any] = dict(
                flow_run_name=f"respond in {channel_name}/{ts}"
            )
            asyncio.create_task(handle_message.with_options(**flow_opts)(payload, db))
    elif payload.type == "url_verification":
        return {"challenge": payload.challenge}
    else:
        raise HTTPException(400, "Invalid event type")

    return {"status": "ok"}
