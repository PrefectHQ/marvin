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
from prefect.blocks.notifications import SlackWebhook
from prefect.states import Completed
from prefect.variables import Variable
from tools import (
    get_latest_prefect_release_notes,
    search_controlflow_docs,
    search_prefect_2x_docs,
    search_prefect_3x_docs,
)

BOT_MENTION = r"<@(\w+)>"
CACHE = JSONBlockState(block_name="marvin-thread-cache")
USER_MESSAGE_MAX_TOKENS = 300

logger = get_logger("slackbot")
warnings.filterwarnings("ignore")


@contextmanager
def engage_marvin_bot(model: str):
    with Assistant(
        model=model,
        name="Marvin (from Hitchhiker's Guide to the Galaxy)",
        tools=[
            get_latest_prefect_release_notes,
            search_prefect_2x_docs,
            search_prefect_3x_docs,
            search_github_issues,
            search_controlflow_docs,
        ],
        instructions=(
            "You are an expert in Python, data engineering, and software development. "
            "When assisting users with Prefect questions, first infer or confirm their "
            "Prefect version. Use the appropriate tools to search Prefect 2.x or 3.x "
            "documentation and GitHub issues related to their query, making multiple "
            "searches as needed. Assume ZERO knowledge of prefect syntax, as its version "
            "specific (YOU MUST USE THE TOOLS). Refine your answer through further research. "
            "Respond to the user in a friendly, concise, and natural manner, always "
            "providing links to your sources. Avoid using markdown formatting unless "
            "in a markdown block, as we are posting your response to slack."
            "The user may also ask about controlflow, in which case you should use the "
            "search_controlflow_docs tool and assume prefect 3.x, since its built on that. "
            "VERY SPARINGLY use a tad of subtle humor in the style of Marvin (paranoid "
            "android from Hitchhiker's Guide to the Galaxy), just once in a while."
        ),
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
            model=cast(str, await Variable.get("marvin_bot_model", "gpt-4o")),
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
    try:
        payload = SlackPayload(**await request.json())
    except Exception as e:
        logger.error(f"Error parsing Slack payload: {e}")
        slack_webhook = await SlackWebhook.load("marvin-bot-pager")
        await slack_webhook.notify(  # type: ignore
            body=f"Error parsing Slack payload: {e}",
            subject="Slackbot Error",
        )
        raise HTTPException(400, "Invalid event type")
    match payload.type:
        case "event_callback":
            print(payload.event)
            # check if the event is a new user joining the workspace. If so, send a welcome message.
            if payload.event.type == "team_join":
                user_id = payload.event.user
                # get the welcome message from the variable store
                message_var = await Variable.get("marvin_welcome_message")
                message = message_var["text"]
                # format the message with the user's id
                f_string = message.format(user_id=user_id)
                # post the message to the user's DM channel
                await task(post_slack_message)(
                    message=(f_string),
                    channel_id=user_id,  # type: ignore
                )
            else:
                channel_name = await get_channel_name(payload.event.channel)
                if channel_name.startswith("D"):
                    # This is a DM channel, we should not respond
                    logger.warning(
                        f"Attempted to respond in DM channel: {channel_name}"
                    )
                    slack_webhook = await SlackWebhook.load("marvin-bot-pager")
                    await slack_webhook.notify(
                        body=f"Attempted to respond in DM channel: {channel_name}",
                        subject="Slackbot DM Warning",
                    )
                    return Completed(message="Skipped DM channel", name="SKIPPED")
                options = dict(
                    flow_run_name=f"respond in {channel_name}/{payload.event.thread_ts}"
                )
                asyncio.create_task(handle_message.with_options(**options)(payload))
        case "url_verification":
            return {"challenge": payload.challenge}
        case _:
            raise HTTPException(400, "Invalid event type")

    return {"status": "ok"}


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY", None):  # TODO: Remove this
        assert (api_key := marvin.settings.openai.api_key), "OPENAI_API_KEY not set"
        os.environ["OPENAI_API_KEY"] = api_key.get_secret_value()

    uvicorn.run(app, host="0.0.0.0", port=4200)
