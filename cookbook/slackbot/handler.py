import asyncio
import re
from copy import deepcopy

from bots import choose_bot
from cachetools import TTLCache
from fastapi import HTTPException
from marvin.utilities.history import History
from marvin.utilities.logging import get_logger
from marvin.utilities.messages import Message
from marvin_recipes.utilities.slack import (
    get_channel_name,
    get_user_name,
    post_slack_message,
)
from prefect.events import Event, emit_event

SLACK_MENTION_REGEX = r"<@(\w+)>"
CACHE = TTLCache(maxsize=1000, ttl=86400)


def _clean(text: str) -> str:
    return text.replace("```python", "```")


async def emit_any_prefect_event(payload: dict) -> Event | None:
    event_type = payload.get("event", {}).get("type", "")

    channel = await get_channel_name(payload.get("event", {}).get("channel", ""))
    user = await get_user_name(payload.get("event", {}).get("user", ""))
    ts = payload.get("event", {}).get("ts", "")

    return emit_event(
        event=f"slack {payload.get('api_app_id')} {event_type}",
        resource={"prefect.resource.id": f"slack.{channel}.{user}.{ts}"},
        payload=payload,
    )


async def generate_ai_response(payload: dict) -> Message:
    event = payload.get("event", {})
    channel_id = event.get("channel", "")
    channel_name = await get_channel_name(channel_id)
    message = event.get("text", "")

    bot_user_id = payload.get("authorizations", [{}])[0].get("user_id", "")

    if match := re.search(SLACK_MENTION_REGEX, message):
        thread_ts = event.get("thread_ts", "")
        ts = event.get("ts", "")
        thread = thread_ts or ts

        mentioned_user_id = match.group(1)

        if mentioned_user_id != bot_user_id:
            get_logger().info(f"Skipping message not meant for the bot: {message}")
            return

        message = re.sub(SLACK_MENTION_REGEX, "", message).strip()
        history = CACHE.get(thread, History())

        bot = choose_bot(payload=payload, history=history)

        get_logger("marvin.Deployment").debug_kv(
            "generate_ai_response",
            f"{bot.name} responding in {channel_name}/{thread}",
            key_style="bold blue",
        )

        ai_message = await bot.run(input_text=message)

        CACHE[thread] = deepcopy(
            bot.history
        )  # make a copy so we don't cache a reference to the history object

        message_content = _clean(ai_message.content)

        await post_slack_message(
            message=message_content,
            channel=channel_id,
            thread_ts=thread,
        )

        return ai_message


async def handle_message(payload: dict) -> dict[str, str]:
    event_type = payload.get("type", "")

    if event_type == "url_verification":
        return {"challenge": payload.get("challenge", "")}
    elif event_type != "event_callback":
        raise HTTPException(status_code=400, detail="Invalid event type")

    await emit_any_prefect_event(payload=payload)

    asyncio.create_task(generate_ai_response(payload))

    return {"status": "ok"}
