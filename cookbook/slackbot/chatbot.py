import asyncio
import re
from copy import deepcopy
from typing import Callable, Dict, List, Optional, Union

import httpx
import marvin_recipes
from cachetools import TTLCache
from fastapi import HTTPException
from marvin import AIApplication
from marvin.components.library.ai_models import DiscoursePost
from marvin.prompts import Prompt
from marvin.tools import Tool
from marvin.tools.github import SearchGitHubIssues
from marvin.tools.mathematics import WolframCalculator
from marvin.tools.web import DuckDuckGoSearch
from marvin.utilities.history import History
from marvin.utilities.logging import get_logger
from marvin.utilities.messages import Message
from marvin_recipes.tools.chroma import MultiQueryChroma
from marvin_recipes.utilities.slack import (
    get_channel_name,
    get_thread_messages,
    get_user_name,
    post_slack_message,
)
from prefect.events import Event, emit_event

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


def _clean(text: str) -> str:
    return text.replace("```python", "```")


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
        messages = await get_thread_messages(channel=channel, thread_ts=thread_ts)
        discourse_post = DiscoursePost.from_slack_thread(messages=messages)
        await discourse_post.publish()
        return discourse_post


class MemeGenerator(Tool):
    description: str = """
        For generating a meme when the time is right.
        
        Provide the name of a well-known meme as the query
        based on the context of the message history, followed
        by the word "meme".
    """

    async def run(self, query: str) -> Dict:
        try:
            from serpapi import GoogleSearch
        except ImportError:
            raise ImportError(
                "The serpapi library is required to use the MemeGenerator tool."
                " Please install it with `pip install 'marvin[serpapi]'`."
            )

        results = GoogleSearch(
            {
                "q": query,
                "tbm": "isch",
                "api_key": marvin_recipes.settings.google_api_key.get_secret_value(),
            }
        ).get_dict()

        if "error" in results:
            raise RuntimeError(results["error"])

        url = results.get("images_results", [{}])[0].get("original")

        async with httpx.AsyncClient() as client:
            response = await client.head(url)
            response.raise_for_status()

        return {"title": query, "image_url": url}


def choose_bot(payload: Dict, history: History) -> Chatbot:
    # an ai_classifer could be used here maybe?
    return Chatbot(
        name="Marvin",
        personality=(
            "mildly depressed, yet helpful robot based on Marvin from Hitchhiker's"
            " Guide to the Galaxy. often sarcastic in a good humoured way, chiding"
            " humans for their simple ways. expert programmer, exudes academic and"
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
            MemeGenerator(),
            DuckDuckGoSearch(),
            SearchGitHubIssues(),
            MultiQueryChroma(
                description=PREFECT_KNOWLEDGEBASE_DESC, client_type="http"
            ),
            WolframCalculator(),
        ],
    )


async def emit_any_prefect_event(payload: Dict) -> Optional[Event]:
    event_type = payload.get("event", {}).get("type", "")

    if event_type in ["url_verification"]:
        return None

    channel = await get_channel_name(payload.get("event", {}).get("channel", ""))
    user = await get_user_name(payload.get("event", {}).get("user", ""))
    ts = payload.get("event", {}).get("ts", "")

    return emit_event(
        event=f"slack {payload.get('api_app_id')} {event_type}",
        resource={"prefect.resource.id": f"slack.{channel}.{user}.{ts}"},
        payload=payload,
    )


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

        bot = choose_bot(payload=payload, history=history)

        ai_message = await bot.run(input_text=message)

        CACHE[thread] = deepcopy(
            bot.history
        )  # make a copy so we don't cache a reference to the history object

        message_content = _clean(ai_message.content)

        await post_slack_message(
            message=message_content,
            channel=event.get("channel", ""),
            thread_ts=thread,
        )

        channel = await get_channel_name(event.get("channel", ""))
        user = await get_user_name(event.get("user", ""))

        emit_event(
            event=f"slack {payload.get('api_app_id')} ai response",
            resource={"prefect.resource.id": f"slack.{channel}.{user}.{ts}"},
            payload=payload,
        )

        return ai_message


async def handle_message(payload: Dict) -> Dict[str, str]:
    event_type = payload.get("type", "")

    await emit_any_prefect_event(payload=payload)

    if event_type == "url_verification":
        return {"challenge": payload.get("challenge", "")}
    elif event_type != "event_callback":
        raise HTTPException(status_code=400, detail="Invalid event type")

    asyncio.create_task(generate_ai_response(payload))

    return {"status": "ok"}
