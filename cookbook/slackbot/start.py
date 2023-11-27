import asyncio
import re

import uvicorn
from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Request
from marvin import Assistant
from marvin.beta.assistants import Thread
from marvin.tools.github import search_github_issues
from marvin.tools.retrieval import multi_query_chroma
from marvin.utilities.slack import post_slack_message

CACHE = TTLCache(maxsize=100, ttl=86400 * 7)
app = FastAPI()
MENTION_REGEX = r"<@(\w+)>"


def select_assistant_given_some(event: dict) -> dict:
    """eventually use the event to select the assistant"""
    return {"name": "marvin", "tools": [multi_query_chroma, search_github_issues]}


async def handle_message(payload: dict):
    event = payload.get("event", {})
    if (user := re.search(MENTION_REGEX, event.get("text", ""))) and user.group(
        1
    ) == payload.get("authorizations", [{}])[0].get("user_id"):
        clean_message = re.sub(MENTION_REGEX, "", event["text"]).strip()
        thread = event.get("thread_ts", event.get("ts", ""))
        assistant_thread = CACHE.get(thread, Thread())
        CACHE[thread] = assistant_thread

        with Assistant(**select_assistant_given_some(event)) as assistant:
            await assistant_thread.add_async(clean_message)
            response = await assistant_thread.run_async(assistant)
            await post_slack_message(
                response.thread.get_messages()[-1].content[0].text.value,
                event["channel"],
                thread,
            )


@app.post("/chat")
async def chat_endpoint(request: Request):
    match (payload := await request.json()).get("type"):
        case "event_callback":
            asyncio.create_task(handle_message(payload))
        case "url_verification":
            return {"challenge": payload.get("challenge", "")}
        case _:
            raise HTTPException(400, "Invalid event type")

    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4200)
