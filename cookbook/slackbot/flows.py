import re

from keywords import handle_keywords
from marvin import Assistant
from marvin.beta.assistants import Thread
from marvin.tools.github import search_github_issues
from marvin.tools.retrieval import multi_query_chroma
from marvin.utilities.logging import get_logger
from marvin.utilities.pydantic import parse_as
from marvin.utilities.redis import redis_client
from marvin.utilities.slack import (
    SLACKBOT_MENTION,
    SlackPayload,
    get_channel_name,
    get_emoji,
    get_workspace_info,
    post_slack_message,
)
from prefect import flow, task
from prefect.states import Completed

MARVIN_SLACKBOT_SETTINGS = dict(
    name="Marvin (from Hitchhiker's Guide to the Galaxy)",
    tools=[task(multi_query_chroma), task(search_github_issues)],
    instructions=(
        "use chroma to search docs and github to search"
        " issues and answer questions about prefect 2.x."
        " you must use your tools in all cases except where"
        " the user simply wants to converse with you."
    ),
)

POSITIVE_REACTIONS = {
    "+1",
    "thumbsup",
    "thumbs_up",
    "white_check_mark",
    "heavy_check_mark",
    "heavy_plus_sign",
}

NEGATIVE_REACTIONS = {
    "-1",
    "thumbsdown",
    "thumbs_down",
    "x",
    "heavy_multiplication_x",
    "no_entry_sign",
    "no_good",
}

DEFAULT_EXPIRATION = 86400 * 7

logger = get_logger("slackbot.handlers")


def cache_bot_message(ts: str):
    """Cache the timestamp of a bot message in Redis."""
    with redis_client() as redis:
        redis.set(f"message:{ts}", "true", ex=DEFAULT_EXPIRATION)


@flow
async def handle_message(payload: SlackPayload):
    user_message = (event := payload.event).text
    cleaned_message = re.sub(SLACKBOT_MENTION, "", user_message).strip()
    logger.debug_kv("Handling slack message", user_message, "green")
    thread = event.thread_ts or event.ts

    with redis_client() as redis:
        if assistant_thread_data := redis.get(f"thread:{thread}"):
            assistant_thread = parse_as(Thread, assistant_thread_data, mode="json")
        else:
            assistant_thread = Thread()

        redis.set(
            f"thread:{thread}",
            assistant_thread.model_dump_json(),
            ex=DEFAULT_EXPIRATION,
        )

        await handle_keywords.submit(
            message=cleaned_message,
            channel_name=await get_channel_name(event.channel),
            asking_user=event.user,
            link=(  # to user's message
                f"{(await get_workspace_info()).get('url')}archives/"
                f"{event.channel}/p{event.ts.replace('.', '')}"
            ),
        )

        with Assistant(**MARVIN_SLACKBOT_SETTINGS) as assistant:
            user_thread_message = await assistant_thread.add_async(cleaned_message)
            await assistant_thread.run_async(assistant)
            ai_messages = assistant_thread.get_messages(
                after_message=user_thread_message.id
            )
            response = await task(post_slack_message)(
                ai_response_text := "\n\n".join(
                    m.content[0].text.value for m in ai_messages
                ),
                channel := event.channel,
                thread,
            )
            cache_bot_message(response.json().get("ts"))
            logger.debug_kv(
                success_msg := f"Responded in {channel}/{thread}",
                ai_response_text,
                "green",
            )

    return Completed(message=success_msg)


@flow
async def handle_reaction_added(payload: SlackPayload, emoji_name: str):
    emoji = await get_emoji(emoji_name)
    if emoji_name in POSITIVE_REACTIONS:
        await save_helpful_answer(payload)
    elif emoji_name in NEGATIVE_REACTIONS:
        await discourage_similar_bad_answers(payload)
    else:
        await task(post_slack_message)(
            message=(
                f"I'm not programmed to react intentionally to {emoji!r}. Please"
                " respond with a positive emoji:"
                f" \n{' | '.join(POSITIVE_REACTIONS)}\n\nOr a negative emoji:"
                f" \n{' | '.join(NEGATIVE_REACTIONS)} to offer feedback on my"
                " responses."
            ),
            channel_id=payload.event.channel,
            thread_ts=payload.event.thread_ts or payload.event.ts,
        )
    return Completed(message=f"Reaction {emoji} processed for {payload.event.item}")


@task
async def save_helpful_answer(payload):
    await task(post_slack_message)(
        message=(
            "Thanks for your feedback! :raised_hands: I've recorded this answer as"
            " helpful."
        ),
        channel_id=payload.event.channel,
        thread_ts=payload.event.thread_ts or payload.event.ts,
    )


@task
async def discourage_similar_bad_answers(payload):
    await task(post_slack_message)(
        message=(
            "Thanks for your feedback! I'll try to avoid giving similar answers in the"
            " future."
        ),
        channel_id=payload.event.channel,
        thread_ts=payload.event.thread_ts or payload.event.ts,
    )
