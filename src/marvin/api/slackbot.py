import asyncio

import httpx
from fastapi import Request, status
from pydantic import BaseModel

import marvin
from marvin.utilities.types import MarvinRouter

router = MarvinRouter(
    tags=["Slack"],
    prefix="/slack",
)


class SlackEvent(BaseModel):
    type: str
    user: str
    text: str
    channel: str
    ts: str


async def _post_message_to_slack(channel: str, message: str, thread_ts: str = None):
    async with httpx.AsyncClient() as client:
        payload = {
            "channel": channel,
            "text": message,
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts

        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": (
                    "Bearer"
                    f" {marvin.config.settings.slack_bot_token.get_secret_value()}"
                )
            },
            json=payload,
        )
        response.raise_for_status()


async def _slack_response(event: SlackEvent):
    bot = marvin.config.settings.slackbot

    await bot.set_thread(thread_lookup_key=f"{event.channel}:{event.user}")

    response = await bot.say(event.text)

    await _post_message_to_slack(event.channel, response.content, event.ts)


@router.post("/events", status_code=status.HTTP_200_OK)
async def handle_slack_events(request: Request):
    payload = await request.json()

    if payload["type"] == "url_verification":
        return payload["challenge"]

    event = SlackEvent(**payload["event"])

    if event.type == "app_mention":
        asyncio.ensure_future(_slack_response(event))

    return {"success": True}
