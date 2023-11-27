import asyncio
import re

import uvicorn
from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Request
from marvin import Assistant
from marvin.beta.assistants import Thread
from marvin.tools.github import search_github_issues
from marvin.tools.retrieval import multi_query_chroma
from marvin.utilities.logging import get_logger
from marvin.utilities.slack import post_slack_message

app = FastAPI()
SLACK_MENTION_REGEX = r"<@(\w+)>"


def get_options_for(event: dict) -> dict:
    return {
        "name": "marvin",
        "tools": [
            multi_query_chroma,
            search_github_issues,
        ],
    }


CACHE = TTLCache(maxsize=1000, ttl=86400)


async def handle(payload: dict):
    event = payload.get("event", {})
    message = event.get("text", "")
    mentioned_user = re.search(SLACK_MENTION_REGEX, message)
    if not mentioned_user or mentioned_user.group(1) != payload.get(
        "authorizations", [{}]
    )[0].get("user_id", ""):
        get_logger().info("Message not for bot")
        return

    clean_message = re.sub(SLACK_MENTION_REGEX, "", message).strip()
    thread = event.get("thread_ts", event.get("ts", ""))

    with Assistant(**get_options_for(event)) as assistant:
        if thread in CACHE:
            assistant_thread = CACHE[thread]
        else:
            assistant_thread = Thread()
            CACHE[thread] = assistant_thread

        await assistant_thread.add_async(clean_message)

        run = await assistant_thread.run_async(assistant)

        ai_response_content = run.thread.get_messages()[-1].content[0].text.value
        await post_slack_message(
            message=ai_response_content,
            channel_id=event.get("channel"),
            thread_ts=thread,
        )


@app.post("/chat")
async def message_endpoint(request: Request):
    payload = await request.json()
    if payload.get("type") == "event_callback":
        asyncio.create_task(handle(payload))
        return {"status": "ok"}
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}
    raise HTTPException(status_code=400, detail="Invalid event type")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4200)
