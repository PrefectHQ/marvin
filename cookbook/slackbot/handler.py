import asyncio
import logging
import random
import re
from contextlib import asynccontextmanager
from copy import deepcopy

from auxillary import get_reduced_kw_relationship_map
from bots import choose_bot
from cachetools import TTLCache
from fastapi import HTTPException
from marvin import ai_fn
from marvin.utilities.async_utils import run_sync
from marvin.utilities.history import History
from marvin.utilities.logging import get_logger
from marvin_recipes.utilities.slack import (
    edit_slack_message,
    get_channel_name,
    get_user_name,
    post_slack_message,
)
from personality import completion_messages, start_messages
from prefect.events import Event, emit_event


class LogCaptureHandler(logging.Handler):
    def __init__(self, channel, ts):
        super().__init__()
        self.channel = channel
        self.ts = ts
        self.records = []

    def emit(self, record):
        if "Function call:" in record.msg:
            tool_name_search = re.search(r"'(.+?)'", record.msg)
            if tool_name_search:
                tool_name = tool_name_search.group(1)
                action = (
                    "started using"
                    if "with payload:" in record.msg
                    else "finished using"
                )
                log_entry = f"\t » {action} {tool_name}"
                self.records.append(log_entry)
                run_sync(edit_slack_message(self.channel, self.ts, log_entry))


@asynccontextmanager
async def stream_logs(name, channel, ts):
    logger = get_logger(name)
    handler = LogCaptureHandler(channel, ts)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%m/%d/%y %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)


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


@ai_fn
def activation_score(message: str, keyword: str, target_relationship: str) -> float:
    """Return a score between 0 and 1 indicating whether the target relationship exists
    between the message and the keyword"""


async def generate_ai_response(payload: dict):
    event = payload.get("event", {})
    channel_id = event.get("channel", "")
    channel_name = await get_channel_name(channel_id)
    message = event.get("text", "")

    keyword_relationships = await get_reduced_kw_relationship_map()
    keywords = [
        keyword for keyword in keyword_relationships.keys() if keyword in message
    ]
    for keyword in keywords:
        target_relationship = keyword_relationships.get(keyword)
        if not target_relationship:
            continue
        score = activation_score(message, keyword, target_relationship)
        if score > 0.5:
            await post_slack_message(
                message=(
                    f"Marvin detected that you are asking about {target_relationship}."
                ),
                channel=channel_id,
            )
            return

    bot_user_id = payload.get("authorizations", [{}])[0].get("user_id", "")

    if match := re.search(SLACK_MENTION_REGEX, message):
        thread_ts = event.get("thread_ts", "")
        ts = event.get("ts", "")
        thread = thread_ts or ts

        mentioned_user_id = match.group(1)

        if mentioned_user_id != bot_user_id:
            get_logger().info(f"Skipping message not meant for the bot: {message}")
            return

        message_content = re.sub(SLACK_MENTION_REGEX, "", message).strip()
        history = CACHE.get(thread, History())

        bot = choose_bot(payload=payload, history=history)

        get_logger("marvin.Deployment").debug(
            f"{bot.name} responding in {channel_name}/{thread}"
        )

        initial_message_response = await post_slack_message(
            message=random.choice(start_messages), channel=channel_id, thread_ts=thread
        )

        thread_ts = initial_message_response.json().get("ts")

        async with stream_logs("marvin.ChatCompletion.handlers", channel_id, thread_ts):
            ai_message = await bot.run(input_text=message_content)

        await edit_slack_message(
            channel_id, thread_ts, random.choice(completion_messages)
        )

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
