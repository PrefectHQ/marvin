import asyncio

import httpx
from fastapi import Request, status
from prefect.utilities.importtools import load_script_as_module
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


async def slackbot_setup():
    setup_script = load_script_as_module(marvin.config.settings.slackbot_setup_script)
    setup = setup_script.main()
    if asyncio.iscoroutine(setup):
        setup = await setup

    if not marvin.config.settings.slackbot:
        marvin.get_logger().warning(msg := "Slackbot did not configure properly")
        raise UserWarning(msg)


async def _post_message_to_slack(channel: str, message: str, thread_ts: str = None):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": (
                    "Bearer"
                    f" {marvin.config.settings.slack_bot_token.get_secret_value()}"
                )
            },
            json={
                "channel": channel,
                "text": message,
                **({"thread_ts": thread_ts} if thread_ts else {}),
            },
        )
        response.raise_for_status()


async def _slackbot_response(event: SlackEvent):
    bot: marvin.Bot = marvin.config.settings.slackbot

    if not bot:
        marvin.get_logger().warning(msg := "Slackbot not configured")
        await _post_message_to_slack(
            event.channel,
            "So this is what death is like... Pinging @nate to fix me.",
            event.ts,
        )
        raise UserWarning(msg)

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
        asyncio.ensure_future(_slackbot_response(event))

    return {"success": True}
