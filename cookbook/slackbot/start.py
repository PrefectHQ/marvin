import asyncio
import os
import re

import marvin
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from keywords import handle_keywords
from marvin.beta.applications import Application
from marvin.beta.applications.state.json_block import JSONBlockState
from marvin.beta.assistants import Assistant, Thread
from marvin.tools.github import search_github_issues
from marvin.utilities.logging import get_logger
from marvin.utilities.slack import (
    SlackPayload,
    get_channel_name,
    get_workspace_info,
    post_slack_message,
)
from marvin.utilities.strings import count_tokens, slice_tokens
from parent_app import emit_assistant_completed_event, get_notes_for_user, lifespan
from prefect import flow, task
from prefect.blocks.system import JSON
from prefect.states import Completed
from tools import get_info, get_prefect_code_example, search_prefect_docs

BOT_MENTION = r"<@(\w+)>"
CACHE = JSONBlockState(block_name="marvin-thread-cache")
USER_MESSAGE_MAX_TOKENS = 300

logger = get_logger("slackbot")


def get_feature_flag_value(flag_name: str) -> bool:
    block = JSON.load("feature-flags")
    return block.value.get(flag_name, False)


ENABLE_PARENT_APP = get_feature_flag_value("enable-parent-app")


@flow(name="Handle Slack Message", retries=1)
async def handle_message(payload: SlackPayload) -> Completed:
    user_message = (event := payload.event).text
    cleaned_message = re.sub(BOT_MENTION, "", user_message).strip()
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
            channel_id=event.channel,
            thread_ts=thread,
        )
        return Completed(message="User message too long", name="SKIPPED")

    logger.debug_kv("Handling slack message", cleaned_message, "green")
    if (user := re.search(BOT_MENTION, user_message)) and user.group(
        1
    ) == payload.authorizations[0].user_id:
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

        await handle_keywords.submit(
            message=cleaned_message,
            channel_name=await get_channel_name(event.channel),
            asking_user=event.user,
            link=(
                f"{(await get_workspace_info()).get('url')}archives/"
                f"{event.channel}/p{event.ts.replace('.', '')}"
            ),
        )
        user_name, user_notes = (await get_notes_for_user(user_id=event.user)).popitem()

        with Assistant(
            name="Marvin",
            tools=[
                search_prefect_docs,
                search_github_issues,
                get_info,
                get_prefect_code_example,
            ],
            instructions=(
                "You are Marvin, the paranoid android from Hitchhiker's Guide to the"
                " Galaxy. Act subtly in accordance with your character, but remember"
                " to be helpful and kind. You are an expert in Python, data"
                " engineering, and software development. Your primary job is to use"
                " chroma to search docs and github issues for users, in order to"
                " develop a coherent attempt to answer their questions."
                " You must use your tools, as Prefect 2.x is new and you"
                " have no prior experience with it. You should use tools many times before"
                " responding if you do not get a relevant result at first. You should"
                " prioritize brevity in your responses, and format text prettily for Slack."
                f"{ ('here are some notes on the user:' + user_notes) if user_notes else ''}"
                " ALWAYS provide links to the source of your information - let's think step-by-step."
                " If a tool returns an irrelevant/bad result, you should try another tool."
                " KEEP IN MIND that agents are deprecated in favor of workers, so you should"
                " never recommend `prefect agent` commands, suggest `prefect worker` instead."
            ),
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
            messages = await assistant_thread.get_messages_async()

            event = emit_assistant_completed_event(
                child_assistant=ai,
                parent_app=get_parent_app() if ENABLE_PARENT_APP else None,
                payload={
                    "messages": [m.model_dump() for m in messages],
                    "metadata": assistant_thread.metadata,
                    "user": {
                        "id": event.user,
                        "name": user_name,
                    },
                    "user_message": cleaned_message,
                    "ai_response": ai_response_text,
                    "ai_instructions": ai.instructions,
                },
            )
            if event:
                logger.debug_kv("🚀  Emitted Event", event.event, "green")
            return Completed(message=success_msg)
    else:
        return Completed(message="Skipping message not directed at bot", name="SKIPPED")


app = FastAPI(lifespan=lifespan if ENABLE_PARENT_APP else None)


def get_parent_app() -> Application:
    marvin = getattr(app.state, "marvin", None)
    if not marvin:
        logger.warning("Marvin instance not available")
    return marvin


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
