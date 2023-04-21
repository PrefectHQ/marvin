import asyncio

import httpx
from fastapi import HTTPException, Request, status
from pydantic import BaseModel

import marvin
from marvin.utilities.strings import convert_md_links_to_slack
from marvin.utilities.types import MarvinRouter

router = MarvinRouter(
    tags=["Slack"],
    prefix="/slack",
)

BOT_SLACK_ID = None


class SlackEvent(BaseModel):
    type: str
    user: str
    text: str
    channel: str
    ts: str
    thread_ts: str = None


async def _get_bot_user():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/users.identity",
            headers={
                "Authorization": (
                    f"Bearer {marvin.settings.slack_api_token.get_secret_value()}"
                ),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
        global BOT_SLACK_ID
        BOT_SLACK_ID = response.json().get("user", {}).get("id", None)


async def _post_message_to_slack(channel: str, message: str, thread_ts: str = None):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": (
                    f"Bearer {marvin.settings.slack_api_token.get_secret_value()}"
                ),
                "Content-Type": "application/json; charset=utf-8",
            },
            json={
                "channel": channel,
                "text": convert_md_links_to_slack(message),
                **({"thread_ts": thread_ts} if thread_ts else {}),
            },
        )
        marvin.get_logger().debug(
            f"sent slack message: {response.json()} to {channel} responding in"
            f" {thread_ts}"
        )
        response.raise_for_status()


async def _slackbot_response(event: SlackEvent):
    try:
        bot = await marvin.Bot.load(marvin.settings.slack_bot_name)
    except HTTPException as e:
        if e.status_code == 404:
            marvin.get_logger().warning(msg := "Slackbot not configured")
            await _post_message_to_slack(
                event.channel,
                "So this is what death is like... Pinging @nate to fix me.",
                event.ts,
            )
            raise UserWarning(msg)
        else:
            raise

    thread = event.thread_ts or event.ts
    await bot.set_thread(thread_lookup_key=f"{event.channel}:{thread}")

    # replace the bot slack id with a recognizable name
    text = event.text.replace(f"<@{BOT_SLACK_ID}>", bot.name).strip()
    response = await bot.say(text)
    await _post_message_to_slack(event.channel, response.content, event.ts)


@router.post("/events", status_code=status.HTTP_200_OK)
async def handle_slack_events(request: Request):
    """This route handles Slack events, including app mentions."""
    payload = await request.json()

    if payload["type"] == "url_verification":
        return payload["challenge"]

    event = SlackEvent(**payload["event"])

    if event.type == "app_mention":
        asyncio.ensure_future(_slackbot_response(event))

    return {"success": True}


async def startup():
    if marvin.settings.slack_api_token.get_secret_value():
        await _get_bot_user()
