import asyncio
import re
from typing import Dict

import httpx
import marvin
from cachetools import TTLCache
from fastapi import HTTPException
from marvin.apps.chatbot import Bot
from marvin.models.history import History
from marvin.models.messages import Message
from marvin.utilities.logging import get_logger

SLACK_MENTION_REGEX = r"<@(\w+)>"
CACHE = TTLCache(maxsize=1000, ttl=86400)


async def post_message(message: str, channel: str) -> httpx.Response:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": (
                    f"Bearer {marvin.settings.slack_api_token.get_secret_value()}"
                )
            },
            json={"channel": channel, "text": message},
        )

    response.raise_for_status()
    return response


async def generate_ai_response(payload: Dict) -> Message:
    event = payload.get("event", {})
    message = event.get("text", "")

    bot_user_id = payload.get("authorizations", [{}])[0].get("user_id", "")

    if match := re.search(SLACK_MENTION_REGEX, message):
        thread_ts = event.get("thread_ts", "")
        mentioned_user_id = match.group(1)

        if mentioned_user_id != bot_user_id:
            get_logger().info(f"Skipping message not meant for the bot: {message}")
            return

        message = re.sub(SLACK_MENTION_REGEX, "", message).strip()
        history = CACHE.get(thread_ts, History())
        bot = Bot(history=history)

        ai_message = await bot.run(input_text=message)

        CACHE[thread_ts] = bot.history
        await post_message(ai_message.content, channel=event.get("channel", ""))

        return ai_message


async def handle_message(payload: Dict) -> Dict[str, str]:
    event_type = payload.get("type", "")

    if event_type == "url_verification":
        return {"challenge": payload.get("challenge", "")}
    elif event_type != "event_callback":
        raise HTTPException(status_code=400, detail="Invalid event type")

    # Run response generation in the background
    asyncio.create_task(generate_ai_response(payload))

    return {"status": "ok"}


if __name__ == "__main__":
    from marvin.deployment import Deployment

    slackbot = Bot(
        personality="A friendly AI assistant",
        instructions="Engage the user in conversation.",
        tools=[handle_message],
    )

    deployment = Deployment(
        component=slackbot,
        app_kwargs={
            "title": "Marvin Slackbot",
            "description": "A Slackbot powered by Marvin",
        },
    )

    deployment.serve()
