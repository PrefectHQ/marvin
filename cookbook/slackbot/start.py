import asyncio
import re
from enum import Enum, auto
from typing import Any, Dict, List, Optional

import controlflow as cf
from fastapi import FastAPI, Request
from marvin.utilities.logging import get_logger
from marvin.utilities.slack import post_slack_message
from marvin.utilities.strings import count_tokens, slice_tokens
from models import Discovery, ExcerptSummary
from prefect import flow
from prefect.states import Completed
from pydantic import BaseModel
from tools import (
    get_more_info_from_user,
    search_knowledgebase,
    user_context,
)

app = FastAPI()
logger = get_logger("slackbot")

BOT_MENTION = r"<@(\w+)>"
USER_MESSAGE_MAX_TOKENS = 300


class EventType(Enum):
    MESSAGE = auto()
    MESSAGE_CHANGED = auto()
    APP_MENTION = auto()
    CHALLENGE = auto()
    UNKNOWN = auto()


class SlackEventAuthorization(BaseModel):
    enterprise_id: Optional[str] = None
    team_id: str
    user_id: str
    is_bot: bool
    is_enterprise_install: bool


class SlackEventMessage(BaseModel):
    type: str
    user: str
    text: str
    ts: str


class SlackEvent(BaseModel):
    type: str
    user: Optional[str] = None
    text: Optional[str] = None
    channel: str
    ts: str
    event_ts: str
    thread_ts: Optional[str] = None
    message: Optional[SlackEventMessage] = None
    previous_message: Optional[Dict[str, Any]] = None
    subtype: Optional[str] = None


class SlackPayload(BaseModel):
    token: str
    team_id: str
    api_app_id: str
    event: SlackEvent
    type: str
    event_id: str
    event_time: int
    authorizations: List[SlackEventAuthorization]
    is_ext_shared_channel: bool
    event_context: str


class SlackChallengeResponse(BaseModel):
    token: str
    challenge: str
    type: str


slackbot = cf.Agent(
    name="Slackbot",
    tools=[search_knowledgebase, get_more_info_from_user],
    instructions=(
        "You are a Slack bot for Prefect. Use *bold* for emphasis. "
        "Always instruct users to *edit their original message* for more info."
    ),
)


@flow(name="Handle Slack Message", retries=1)
async def handle_message(payload: SlackPayload) -> Completed:
    event = payload.event
    user_message = event.text or (event.message.text if event.message else "")
    cleaned_message = re.sub(BOT_MENTION, "", user_message).strip()
    thread = event.thread_ts or event.ts

    if (count := count_tokens(cleaned_message)) > USER_MESSAGE_MAX_TOKENS:
        exceeded_amt = count - USER_MESSAGE_MAX_TOKENS
        await post_slack_message(
            message=(
                f"Your message was too long by {exceeded_amt} tokens - please shorten "
                f"it and try again.\n\nFor reference, here's your message at the "
                f"allowed limit:\n> {slice_tokens(cleaned_message, USER_MESSAGE_MAX_TOKENS)}"
            ),
            channel_id=event.channel,
            thread_ts=thread,
        )
        return Completed(message="User message too long", name="SKIPPED")

    logger.debug_kv("Handling slack message", cleaned_message, "green")

    user_id = event.user or (event.message.user if event.message else None)

    if (
        is_edit := event.subtype == "message_changed"
        or (user := re.search(BOT_MENTION, user_message))
        and user.group(1) == payload.authorizations[0].user_id
    ):
        with user_context(user_id, event.channel, thread):
            response = await asyncio.to_thread(answer_slack_question, event)

        if is_edit:
            response = f"I've detected an edit to your message. Here's my updated response:\n\n{response}"

        await post_slack_message(
            message=response, channel_id=event.channel, thread_ts=thread
        )

    return Completed(message="Message handled successfully")


@cf.flow(agents=[slackbot])
def answer_slack_question(event: SlackEvent):
    discovery = cf.Task(
        "Gather user's question and Prefect version. If more info is needed, "
        "use get_more_info_from_user to ask them to *edit their original message*.",
        result_type=Discovery,
        context={"event": event},
    )

    summary = cf.Task(
        "Summarize the answer from the knowledgebase",
        user_access=True,
        context=dict(discovery=discovery),
        result_type=ExcerptSummary,
    )

    return cf.Task(
        "Compose the final answer",
        context=dict(summary=summary),
    )


@app.post("/chat")
async def slack_events(request: Request) -> dict:
    body = await request.json()

    if "challenge" in body:
        return SlackChallengeResponse(**body)

    try:
        payload = SlackPayload(**body)
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return {"status": "error", "message": "Invalid payload"}

    if payload.type == "event_callback":
        asyncio.create_task(handle_message(payload))

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("start:app", host="0.0.0.0", port=4200, reload=True)
