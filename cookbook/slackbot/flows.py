import re

import redis
from keywords import handle_keywords
from marvin import Assistant
from marvin.beta.assistants import Thread
from marvin.tools.github import search_github_issues
from marvin.tools.retrieval import multi_query_chroma
from marvin.utilities.logging import get_logger
from marvin.utilities.pydantic import parse_as
from marvin.utilities.slack import (
    SlackPayload,
    get_channel_name,
    get_workspace_info,
    post_slack_message,
)
from prefect import flow, task
from prefect.states import Completed

BOT_MENTION = r"<@(\w+)>"
REDIS_HOST = "redis"  # Assuming environment variable or hardcoded
redis_client = redis.StrictRedis(
    host=REDIS_HOST, port=6379, db=0, decode_responses=True
)
logger = get_logger("slackbot.handlers")


def cache_bot_message(ts: str):
    """Cache the timestamp of a bot message in Redis."""
    redis_client.set(ts, "true", ex=86400 * 7)


@flow
async def handle_message(payload: SlackPayload):
    user_message = (event := payload.event).text
    cleaned_message = re.sub(BOT_MENTION, "", user_message).strip()
    logger.debug_kv("Handling slack message", user_message, "green")
    if (user := re.search(BOT_MENTION, user_message)) and user.group(
        1
    ) == payload.authorizations[0].user_id:
        thread = event.thread_ts or event.ts

        if assistant_thread_data := redis_client.get(thread):
            assistant_thread = parse_as(Thread, assistant_thread_data, mode="json")
        else:
            assistant_thread = Thread()

        redis_client.set(thread, assistant_thread.model_dump_json())

        await handle_keywords.submit(
            message=cleaned_message,
            channel_name=await get_channel_name(event.channel),
            asking_user=event.user,
            link=(  # to user's message
                f"{(await get_workspace_info()).get('url')}archives/"
                f"{event.channel}/p{event.ts.replace('.', '')}"
            ),
        )

        with Assistant(
            name="Marvin (from Hitchhiker's Guide to the Galaxy)",
            tools=[task(multi_query_chroma), task(search_github_issues)],
            instructions=(
                "use chroma to search docs and github to search"
                " issues and answer questions about prefect 2.x."
                " you must use your tools in all cases except where"
                " the user simply wants to converse with you."
            ),
        ) as assistant:
            user_thread_message = await assistant_thread.add_async(cleaned_message)
            await assistant_thread.run_async(assistant)
            ai_messages = assistant_thread.get_messages(
                after_message=user_thread_message.id
            )
            await task(post_slack_message)(
                ai_response_text := "\n\n".join(
                    m.content[0].text.value for m in ai_messages
                ),
                channel := event.channel,
                thread,
            )
            logger.debug_kv(
                success_msg := f"Responded in {channel}/{thread}",
                ai_response_text,
                "green",
            )
            return Completed(message=success_msg)
    else:
        return Completed(
            message="Skipping handling for message not directed at bot", name="SKIPPED"
        )


@flow
async def handle_reaction_added(payload: SlackPayload, emoji_name: str):
    logger.info(f"Emoji added to bot's message: {emoji_name}")
    return Completed(message=f"Handled emoji: {emoji_name}")
