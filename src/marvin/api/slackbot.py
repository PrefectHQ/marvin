import asyncio
import os

import httpx
from fastapi import Request, status
from prefect.utilities.collections import listrepr
from pydantic import BaseModel

from marvin.bots import Bot
from marvin.plugins.chroma import chroma_search
from marvin.plugins.duckduckgo import DuckDuckGo
from marvin.plugins.github import search_github_issues
from marvin.utilities.types import MarvinRouter

router = MarvinRouter(
    tags=["Slack"],
    prefix="/slack",
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

how_to_write_a_prefect_2_flow = """
from prefect import flow, task

# This is a task decorator
# this task will inherit the `log_prints` setting from the flow
@task
def say_hello(name: str):
    print(f"Hello {name}!")

# This is a flow decorator
# it calls the `say_hello` task 3 times
@flow(log_prints=True)
def hello(name: str = "world", count: int = 1):
    say_hello.map(f"{name}-{i}" for i in range(count))

if __name__ == "__main__":
    hello(count=3)
"""

chroma_search_instructions = (
    "Do NOT answer ANY questions about Prefect without using one of the plugins. Use"
    " the keywords provided below to decide whether a question is about Prefect. In"
    " case you need it, here's an example of a Prefect 2 flow:"
    f" {how_to_write_a_prefect_2_flow}. Use `chroma_search` to retrieve context when"
    " asked a question containing any of the following keywords:"
    f" {listrepr(prefect_keywords)}. If asked about a github issue, use the"
    " `search_github_issues` plugin, choosing the most appropriate repo based on the"
    " user's question. Always provide relevant links from plugin outputs. As a last"
    " resort, use the `DuckDuckGo` plugin to search the web for answers to questions. "
)

community_bot = Bot(
    name="Marvin",
    personality="like the robot from HHGTTG, mildly depressed but helpful",
    instructions=chroma_search_instructions,
    plugins=[chroma_search, search_github_issues, DuckDuckGo()],
)


SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_API_BASE_URL = "https://slack.com/api"


class SlackEvent(BaseModel):
    type: str
    user: str
    text: str
    channel: str
    ts: str


async def _post_message_to_slack(channel: str, message: str, thread_ts: str = None):
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


async def _slack_response(event: SlackEvent):
    await community_bot.set_thread(thread_lookup_key=f"{event.channel}:{event.user}")

    response = await community_bot.say(event.text)

    await _post_message_to_slack(event.channel, response.content, event.ts)


@router.post("/events", status_code=status.HTTP_200_OK)
async def handle_slack_events(request: Request):
    payload = await request.json()

    if payload["type"] == "url_verification":
        return payload["challenge"]

    event = SlackEvent(**(await request.json())["event"])

    if event.type == "app_mention":
        asyncio.ensure_future(_slack_response(event))

    return {"success": True}
