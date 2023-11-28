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
from marvin.utilities.slack import SlackPayload, post_slack_message
from prefect import flow, task
from prefect.states import Completed

app = FastAPI()
BOT_MENTION = r"<@(\w+)>"
CACHE = TTLCache(maxsize=100, ttl=86400 * 7)


@flow
async def handle_message(payload: SlackPayload):
    logger = get_logger("slackbot")
    user_message = (event := payload.event).text
    cleaned_message = re.sub(BOT_MENTION, "", user_message).strip()
    logger.debug_kv("Handling slack message", user_message, "green")
    if (user := re.search(BOT_MENTION, user_message)) and user.group(
        1
    ) == payload.authorizations[0].user_id:
        thread = event.thread_ts or event.ts
        assistant_thread = CACHE.get(thread, Thread())
        CACHE[thread] = assistant_thread

        with Assistant(
            name="Marvin (from Hitchhiker's Guide to the Galaxy)",
            tools=[task(multi_query_chroma), task(search_github_issues)],
            instructions=(
                "use chroma to search docs and github to search"
                " issues and answer questions about prefect 2.x."
                " you must use your tools in all cases except where"
                " the user simply wants to converse with you."
            ),
        ) as assistant:
            user_thread_message = await assistant_thread.add_async(cleaned_message)
            await assistant_thread.run_async(assistant)
            ai_messages = assistant_thread.get_messages(
                after_message=user_thread_message.id
            )
            await task(post_slack_message)(
                ai_response_text := "\n\n".join(
                    m.content[0].text.value for m in ai_messages
                ),
                channel := event.channel,
                thread,
            )
            logger.debug_kv(
                success_msg := f"Responded in {channel}/{thread}",
                ai_response_text,
                "green",
            )
            return Completed(message=success_msg)
    else:
        return Completed(
            message="Skipping handling for message not directed at bot", name="SKIPPED"
        )


@app.post("/chat")
async def chat_endpoint(request: Request):
    payload = SlackPayload(**await request.json())
    match payload.type:
        case "event_callback":
            options = dict(
                flow_run_name=f"respond in {payload.event.channel}",
                retries=1,
            )
            asyncio.create_task(handle_message.with_options(**options)(payload))
        case "url_verification":
            return {"challenge": payload.challenge}
        case _:
            raise HTTPException(400, "Invalid event type")

    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4200)
