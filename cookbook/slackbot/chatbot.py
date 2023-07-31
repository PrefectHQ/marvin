import asyncio
import re
from copy import deepcopy
from typing import Callable, Dict, List, Union

import httpx
import marvin
from cachetools import TTLCache
from fastapi import HTTPException
from marvin import AIApplication
from marvin.components.library.ai_models import DiscoursePost
from marvin.prompts import Prompt
from marvin.tools import Tool
from marvin.tools.github import SearchGitHubIssues
from marvin.tools.mathematics import WolframCalculator
from marvin.tools.web import DuckDuckGoSearch, VisitUrl
from marvin.utilities.history import History
from marvin.utilities.logging import get_logger
from marvin.utilities.messages import Message
from marvin.utilities.strings import convert_md_links_to_slack
from marvin_recipes.tools.chroma import MultiQueryChroma

DEFAULT_NAME = "Marvin"
DEFAULT_PERSONALITY = "A friendly AI assistant"
DEFAULT_INSTRUCTIONS = "Engage the user in conversation."


SLACK_MENTION_REGEX = r"<@(\w+)>"
CACHE = TTLCache(maxsize=1000, ttl=86400)
PREFECT_KNOWLEDGEBASE_DESC = """
    Retrieve document excerpts from a knowledge-base given a query.
    
    This knowledgebase contains information about Prefect, a workflow management system.
    Documentation, forum posts, and other community resources are indexed here.
    
    This tool is best used by passing multiple short queries, such as:
    ["k8s worker", "work pools", "deployments"]
"""


class Chatbot(AIApplication):
    name: str = DEFAULT_NAME
    personality: str = DEFAULT_PERSONALITY
    instructions: str = DEFAULT_INSTRUCTIONS
    tools: List[Union[Tool, Callable]] = ([],)

    def __init__(
        self,
        name: str = DEFAULT_NAME,
        personality: str = DEFAULT_PERSONALITY,
        instructions: str = DEFAULT_INSTRUCTIONS,
        state=None,
        tools: list[Union[Tool, Callable]] = [],
        additional_prompts: list[Prompt] = None,
        **kwargs,
    ):
        description = f"""
            You are a chatbot - your name is {name}.
            
            You must respond to the user in accordance with
            your personality and instructions.
            
            Your personality is: {personality}.
            
            Your instructions are: {instructions}.
            """
        super().__init__(
            name=name,
            description=description,
            tools=tools,
            state=state or {},
            state_enabled=False if state is None else True,
            plan_enabled=False,
            additional_prompts=additional_prompts or [],
            **kwargs,
        )


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


def _clean(text: str) -> str:
    return text.replace("```python", "```")


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
            instructions=(
                "Answer user questions in accordance with your personality."
                " Research on behalf of the user using your tools and do not"
                " answer questions without searching the knowledgebase."
                " Your responses will be displayed in Slack, and should be"
                " formatted accordingly, in particular, ```code blocks```"
                " should not be prefaced with a language name."
            ),
            history=history,
            tools=[
                SlackThreadToDiscoursePost(payload=payload),
                VisitUrl(),
                DuckDuckGoSearch(),
                SearchGitHubIssues(),
                MultiQueryChroma(
                    description=PREFECT_KNOWLEDGEBASE_DESC, client_type="http"
                ),
                WolframCalculator(),
            ],
        )

        ai_message = await bot.run(input_text=message)

        CACHE[thread] = deepcopy(
            bot.history
        )  # make a copy so we don't cache a reference to the history object

        message_content = _clean(ai_message.content)

        await _post_message(
            message=message_content,
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
