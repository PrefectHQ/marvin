import asyncio
import os
import re
import warnings
from contextlib import contextmanager
from typing import cast

import marvin
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from marvin.beta.applications.state.json_block import JSONBlockState
from marvin.beta.assistants import Assistant, Thread
from marvin.tools.github import search_github_issues
from marvin.utilities.logging import get_logger
from marvin.utilities.slack import (
    SlackPayload,
    get_channel_name,
    post_slack_message,
)
from marvin.utilities.strings import count_tokens, slice_tokens
from prefect import flow, task
from prefect.states import Completed
from prefect.variables import Variable
from tools import (
    get_info,
    search_prefect_2x_docs,
    search_prefect_3x_docs,
)

BOT_MENTION = r"<@(\w+)>"
CACHE = JSONBlockState(block_name="marvin-thread-cache")
USER_MESSAGE_MAX_TOKENS = 300

logger = get_logger("slackbot")
warnings.filterwarnings("ignore")


@contextmanager
def engage_marvin_bot(instructions: str):
    with Assistant(
        model=cast(str, Variable.get("marvin_bot_model", "gpt-4o")),
        name="Marvin (from Hitchhiker's Guide to the Galaxy)",
        tools=[
            search_prefect_2x_docs,
            search_prefect_3x_docs,
            search_github_issues,
            get_info,
        ],
        instructions=instructions,
    ) as ai:
        yield ai


@flow(name="Handle Slack Message", retries=1)
async def handle_message(payload: SlackPayload):
    assert (event := payload.event)
    user_message = event.text
    cleaned_message = re.sub(BOT_MENTION, "", user_message).strip()  # type: ignore
    thread = event.thread_ts or event.ts
    if (count := count_tokens(cleaned_message)) > USER_MESSAGE_MAX_TOKENS:
        exceeded_amt = count - USER_MESSAGE_MAX_TOKENS
        await task(post_slack_message)(
            message=(
                f"Your message was too long by {exceeded_amt} tokens - please shorten"
                " it and try again.\n\n For reference, here's your message at the"
                " allowed limit:\n>"
                f" {slice_tokens(cleaned_message, USER_MESSAGE_MAX_TOKENS)}"
            ),
            channel_id=event.channel,  # type: ignore
            thread_ts=thread,
        )
        return Completed(message="User message too long", name="SKIPPED")

    logger.debug_kv("Handling slack message", cleaned_message, "green")
    if (user := re.search(BOT_MENTION, user_message)) and user.group(
        1
    ) == payload.authorizations[0].user_id:  # type: ignore
        assistant_thread = (
            Thread.model_validate_json(stored_thread_data)
            if (stored_thread_data := CACHE.value.get(thread))
            else Thread()
        )
        logger.debug_kv(
            "🧵  Thread data",
            stored_thread_data or f"No stored thread data found for {thread}",
            "blue",
        )
        with engage_marvin_bot(
            instructions=await Variable.get("marvin_bot_instructions")
        ) as ai:
            logger.debug_kv(
                f"🤖  Running assistant {ai.name} with instructions",
                ai.instructions,
                "blue",
            )
            user_thread_message = await assistant_thread.add_async(cleaned_message)
            await assistant_thread.run_async(ai)
            ai_messages = await assistant_thread.get_messages_async(
                after_message=user_thread_message.id
            )

            CACHE.set_state(CACHE.value | {thread: assistant_thread.model_dump_json()})

            await task(post_slack_message)(
                ai_response_text := "\n\n".join(
                    m.content[0].text.value for m in ai_messages
                ),
                channel_id=(channel := event.channel),
                thread_ts=thread,
            )
            logger.debug_kv(
                success_msg
                := f"Responded in {await get_channel_name(channel)}/{thread}",
                ai_response_text,
                "green",
            )

            return Completed(message=success_msg)
    else:
        return Completed(message="Skipping message not directed at bot", name="SKIPPED")


app = FastAPI()


@app.post("/chat")
async def chat_endpoint(request: Request):
    payload = SlackPayload(**await request.json())
    match payload.type:
        case "event_callback":
            options = dict(
                flow_run_name=(
                    "respond in"
                    f" {await get_channel_name(payload.event.channel)}/{payload.event.thread_ts}"
                )
            )
            asyncio.create_task(handle_message.with_options(**options)(payload))
        case "url_verification":
            return {"challenge": payload.challenge}
        case _:
            raise HTTPException(400, "Invalid event type")

    return {"status": "ok"}


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY", None):  # TODO: Remove this
        os.environ["OPENAI_API_KEY"] = marvin.settings.openai.api_key.get_secret_value()

    uvicorn.run(app, host="0.0.0.0", port=4200)
