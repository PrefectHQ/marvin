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
    get_workspace_info,
    post_slack_message,
)
from personality import completion_messages, start_messages
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
from prefect.blocks.system import Secret, String


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
                log_entry = f"\t » {action} **{tool_name}**"
                self.records.append(log_entry)
                run_sync(edit_slack_message(log_entry, self.channel, self.ts))


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


@ai_fn
def activation_score(message: str, keyword: str, target_relationship: str) -> float:
    """Return a score between 0 and 1 indicating whether the target relationship exists
    between the message and the keyword"""


@task
async def handle_keywords(message: str, channel_name: str, asking_user: str, link: str):
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
                    f"A user ({asking_user}) just asked a question in"
                    f" {channel_name} that contains the keyword `{keyword}`, and I'm"
                    f" {score*100:.0f}% sure that their message indicates the"
                    f" following:\n\n**{target_relationship!r}**.\n\n[Go to"
                    f" message]({link})"
                ),
                channel_id=(await String.load("ask-marvin-tests-channel-id")).value,
                auth_token=(await Secret.load("slack-api-token")).get(),
            )
            return


@flow
async def generate_ai_response(payload: dict):
    event = payload.get("event", {})
    channel_id, message = event.get("channel", ""), event.get("text", "")
    user_name, channel_name = await asyncio.gather(
        get_user_name(event.get("user", "")), get_channel_name(channel_id)
    )
    link = (  # to user's message
        f"{(await get_workspace_info()).get('url')}archives/"
        f"{channel_id}/p{event.get('ts').replace('.', '')}"
    )

    await handle_keywords.submit(
        message=message,
        channel_name=channel_name,
        asking_user=event.get("user", ""),
        link=link,
    )

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

        bot = task(choose_bot)(payload=payload, history=history)

        get_logger(f"slackbot.{bot.name}").debug(
            f"{bot.name} responding in {channel_name}/{thread}"
        )

        initial_message_response = await task(post_slack_message).with_options(
            task_run_name=f"post {bot.name}'s acknowledgement"
        )(
            message=f":hourglass_flowing_sand: {random.choice(start_messages)}",
            channel_id=channel_id,
            thread_ts=thread,
        )

        response_ts = initial_message_response.json().get("ts")

        async with stream_logs(
            "marvin.ChatCompletion.handlers", channel_id, response_ts
        ):
            ai_message = await bot.run(input_text=message_content)

        await task(edit_slack_message).with_options(
            task_run_name=f"mark completion of {bot.name}'s tool loop"
        )(
            new_text=f":white_check_mark: {random.choice(completion_messages)}\n\n",
            channel_id=channel_id,
            thread_ts=response_ts,
        )

        ai_response_content = _clean(ai_message.content)

        await task(edit_slack_message).with_options(
            task_run_name=f"add {bot.name}'s response to message"
        )(
            new_text=f"\n:robot_face: :speech_balloon: {ai_response_content}",
            channel_id=channel_id,
            thread_ts=response_ts,
            delimiter="",  # no newline
        )

        CACHE[thread] = deepcopy(
            bot.history
        )  # make a copy so we don't cache a reference to the history object

        await create_markdown_artifact(
            markdown=(
                f"#**{channel_name.upper()}** | {thread}\n"
                f"**{user_name}**: {message_content}\n"
                f"**{bot.name}**: {ai_response_content}\n"
                f"\n\n[Find thread in slack]({link})"
            ),
            key=f"marvin-{channel_name}-{int(float(thread))}",
            description="A single message/response pair between a user and slackbot",
        )


async def handle_message(payload: dict) -> dict[str, str]:
    event_type = payload.get("type", "")

    if event_type == "url_verification":
        return {"challenge": payload.get("challenge", "")}
    elif event_type != "event_callback":
        raise HTTPException(status_code=400, detail="Invalid event type")

    asyncio.create_task(generate_ai_response(payload))

    return {"status": "ok"}
