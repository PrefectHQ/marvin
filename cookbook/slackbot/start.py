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

app = FastAPI()
BOT_MENTION_REGEX = r"<@(\w+)>"
CACHE = TTLCache(maxsize=100, ttl=86400 * 7)


async def handle_message(payload: dict):
    event = payload.get("event", {})
    user_msg = event.get("text", "")
    if (user := re.search(BOT_MENTION_REGEX, user_msg)) and user.group(
        1
    ) == payload.get("authorizations", [{}])[0].get("user_id"):
        thread = event.get("thread_ts", event.get("ts", ""))
        assistant_thread = CACHE.get(thread, Thread())
        CACHE[thread] = assistant_thread

        with Assistant(
            name="Marvin (from Hitchhiker's Guide to the Galaxy)",
            tools=[multi_query_chroma, search_github_issues],
            instructions=(
                "use chroma to search docs and github to search"
                " issues and answer questions about prefect 2.x."
                " you must use your tools in all cases except where"
                " the user simply wants to converse with you."
            ),
        ) as assistant:
            await assistant_thread.add_async(
                re.sub(BOT_MENTION_REGEX, "", user_msg).strip()
            )
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
            asyncio.create_task(handle_message(payload))  # background the work
        case "url_verification":
            return {"challenge": payload.get("challenge", "")}
        case _:
            raise HTTPException(400, "Invalid event type")

    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4200)
