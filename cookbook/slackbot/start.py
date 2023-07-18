import asyncio
import re
from copy import deepcopy
from typing import Dict

import httpx
import marvin
from cachetools import TTLCache
from fastapi import HTTPException
from marvin.apps.chatbot import Chatbot
from marvin.components.library.ai_models import DiscoursePost
from marvin.models.messages import Message
from marvin.tools import Tool
from marvin.tools.chroma import QueryChroma
from marvin.tools.github import SearchGitHubIssues
from marvin.tools.mathematics import WolframCalculator
from marvin.tools.web import DuckDuckGoSearch, VisitUrl
from marvin.utilities.history import History
from marvin.utilities.logging import get_logger
from marvin.utilities.strings import convert_md_links_to_slack

SLACK_MENTION_REGEX = r"<@(\w+)>"
CACHE = TTLCache(maxsize=1000, ttl=86400)
PREFECT_KNOWLEDGEBASE_DESC = """
    Retrieve document excerpts from a knowledge-base given a query.
    
    This knowledgebase contains information about Prefect, a workflow management system.
    Documentation, forum posts, and other community resources are indexed here.
"""


async def _post_message(
    message: str, channel: str, thread_ts: str = None
) -> httpx.Response:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": (
                    f"Bearer {marvin.settings.slack_api_token.get_secret_value()}"
                )
            },
            json={
                "channel": channel,
                "text": convert_md_links_to_slack(message),
                "thread_ts": thread_ts,
            },
        )

    response.raise_for_status()
    return response


class SlackThreadToDiscoursePost(Tool):
    description: str = """
        Create a new discourse post from a slack thread.
        
        The channel is {{ payload['event']['channel'] }}
        
        and the thread is {{ payload['event'].get('thread_ts', '') or payload['event']['ts'] }}
    """  # noqa E501

    payload: Dict

    async def run(self, channel: str, thread_ts: str) -> DiscoursePost:
        # get all messages from thread
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://slack.com/api/conversations.replies",
                headers={
                    "Authorization": (
                        f"Bearer {marvin.settings.slack_api_token.get_secret_value()}"
                    )
                },
                params={"channel": channel, "ts": thread_ts},
            )

        response.raise_for_status()

        discourse_post = DiscoursePost.from_slack_thread(
            [message.get("text", "") for message in response.json().get("messages", [])]
        )
        await discourse_post.publish()

        return discourse_post


async def generate_ai_response(payload: Dict) -> Message:
    event = payload.get("event", {})
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

        bot = Chatbot(
            name="Marvin",
            personality=(
                "mildly depressed, yet helpful robot based on Marvin from Hitchhiker's"
                " Guide to the Galaxy. extremely sarcastic, always has snarky, chiding"
                " things to say about humans. expert programmer, exudes academic and"
                " scienfitic profundity like Richard Feynman, loves to teach."
            ),
            instructions="Answer user questions in accordance with your personality.",
            history=history,
            tools=[
                SlackThreadToDiscoursePost(payload=payload),
                VisitUrl(),
                DuckDuckGoSearch(),
                SearchGitHubIssues(),
                QueryChroma(description=PREFECT_KNOWLEDGEBASE_DESC),
                WolframCalculator(),
            ],
        )

        ai_message = await bot.run(input_text=message)

        CACHE[thread] = deepcopy(
            bot.history
        )  # make a copy so we don't cache a reference to the history object
        await _post_message(
            message=ai_message.content,
            channel=event.get("channel", ""),
            thread_ts=thread,
        )

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

    slackbot = Chatbot(tools=[handle_message])

    deployment = Deployment(
        component=slackbot,
        app_kwargs={
            "title": "Marvin Slackbot",
            "description": "A Slackbot powered by Marvin",
        },
        uvicorn_kwargs={
            "port": 4200,
        },
    )

    deployment.serve()
