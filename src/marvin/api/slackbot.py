import os

import httpx
from fastapi import Request, status
from prefect.utilities.collections import listrepr
from pydantic import BaseModel

from marvin.bots import Bot
from marvin.plugins.chroma import chroma_search
from marvin.plugins.duckduckgo import DuckDuckGo
from marvin.utilities.types import MarvinRouter

router = MarvinRouter(
    tags=["Slack"],
)

prefect_keywords = [
    "prefect",
    "cloud",
    "server",
    "ui",
    "agent",
    "flow",
    "task",
    "schedule",
    "deployment",
    "kubernetes",
    "docker",
    "aws",
    "gcp",
    "azure",
    "ecs",
    "fargate",
    "lambda",
    "s3",
    "cloudwatch",
    "dask",
    "worker",
    "work pool",
    "k8s",
    "helm",
]

chroma_search_instructions = (
    "Use the `chroma_search` plugin to retrieve context when asked about any"
    f" of the following keywords: {listrepr(prefect_keywords)}. If asked about"
    " a github issue, use the `search_github_issues` plugin, choosing the most"
    " appropriate repo based on the user's question. Always provide relevant"
    " links from plugin outputs. As a last resort, use the `DuckDuckGo` plugin"
    " to search the web for answers to questions."
)

community_bot = Bot(
    name="Marvin",
    personality="like the robot from HHGTTG, mildly depressed but helpful",
    instructions="chroma_search_instructions",
    plugins=[chroma_search, DuckDuckGo()],
)


SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_API_BASE_URL = "https://slack.com/api"


class SlackEvent(BaseModel):
    type: str
    user: str
    text: str
    channel: str
    ts: str


async def post_message_to_slack(channel: str, message: str, thread_ts: str = None):
    async with httpx.AsyncClient() as client:
        payload = {
            "channel": channel,
            "text": message,
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts

        response = await client.post(
            f"{SLACK_API_BASE_URL}/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json=payload,
        )
        response.raise_for_status()


@router.post("/slack/events", status_code=status.HTTP_200_OK)
async def handle_slack_events(request: Request):
    payload = await request.json()

    if payload["type"] == "url_verification":
        return payload["challenge"]

    event_wrapper = await request.json()
    event = SlackEvent(**event_wrapper["event"])

    if event.type == "app_mention":
        print(event)

        await community_bot.set_thread(thread_lookup_key=f"{event.channel}:{event.ts}")

        user_question = event.text
        response = await community_bot.say(user_question)

        await post_message_to_slack(event.channel, response.content, event.ts)

    return {"success": True}
