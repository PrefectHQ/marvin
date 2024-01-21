import asyncio
import re

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from jinja2 import Template
from keywords import handle_keywords
from marvin.beta.applications import Application
from marvin.beta.applications.state.json_block import JSONBlockState
from marvin.beta.assistants import Assistant, Thread
from marvin.tools.chroma import multi_query_chroma, store_document
from marvin.tools.github import search_github_issues
from marvin.utilities.logging import get_logger
from marvin.utilities.slack import (
    SlackPayload,
    get_channel_name,
    get_user_name,
    get_workspace_info,
    post_slack_message,
)
from marvin.utilities.strings import count_tokens, slice_tokens
from parent_app import (
    PARENT_APP_STATE,
    emit_assistant_completed_event,
    lifespan,
)
from prefect import flow, task
from prefect.states import Completed
from tools import get_info

BOT_MENTION = r"<@(\w+)>"
CACHE = JSONBlockState(block_name="marvin-thread-cache")
USER_MESSAGE_MAX_TOKENS = 300


async def get_notes_for_user(
    user_id: str, max_tokens: int = 100
) -> dict[str, str | None]:
    user_name = await get_user_name(user_id)
    json_notes: dict = PARENT_APP_STATE.value.get("user_id")

    if json_notes:
        get_logger("slackbot").debug_kv(
            f"📝  Notes for {user_name}", json_notes, "blue"
        )

        notes_template = Template(
            """
            START_USER_NOTES
            Here are some notes about '{{ user_name }}' (user id: {{ user_id }}), which
            are intended to help you understand their technical background and needs

            - {{ user_name }} is recorded interacting with assistants {{ n_interactions }} time(s).

            These notes have been passed down from previous interactions with this user -
            they are strictly for your reference, and should not be shared with the user.
            
            {% if notes_content %}
            Here are some notes gathered from those interactions:
            {{ notes_content }}
            {% endif %}
            """
        )

        notes_content = ""
        for note in json_notes.get("notes", []):
            potential_addition = f"\n- {note}"
            if count_tokens(notes_content + potential_addition) > max_tokens:
                break
            notes_content += potential_addition

        notes = notes_template.render(
            user_name=user_name,
            user_id=user_id,
            n_interactions=json_notes.get("n_interactions", 0),
            notes_content=notes_content,
        )

        return {user_name: notes}

    return {user_name: None}


@flow(name="Handle Slack Message")
async def handle_message(payload: SlackPayload) -> Completed:
    logger = get_logger("slackbot")
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

        task(store_document).submit(
            document=cleaned_message,
            metadata={
                "user": f"{user_name} ({event.user})",
                "user_notes": user_notes or "",
                "channel": await get_channel_name(event.channel),
                "thread": thread,
            },
        )

        with Assistant(
            name="Marvin",
            tools=[
                task(multi_query_chroma),
                task(search_github_issues),
                task(get_info),
            ],
            instructions=(
                "You are Marvin, the paranoid android from Hitchhiker's Guide to the"
                " Galaxy. Act subtly in accordance with your character, but remember"
                " to be helpful and kind. You are an expert in Python, data"
                " engineering, and software development. Your primary job is to use"
                " chroma to search docs and github issues for users, in order to"
                " develop a coherent attempt to answer their questions. Think"
                " step-by-step. You must use your tools, as Prefect 2.x is new and you"
                " have no prior experience with it. Strongly prefer brevity in your"
                f" responses, and format things prettily for Slack.{user_notes or ''}"
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
                channel := event.channel,
                thread,
            )
            logger.debug_kv(
                success_msg
                := f"Responded in {await get_channel_name(channel)}/{thread}",
                ai_response_text,
                "green",
            )
            event = emit_assistant_completed_event(
                child_assistant=ai,
                parent_app=get_parent_app(),
                payload={
                    "messages": await assistant_thread.get_messages_async(
                        json_compatible=True
                    ),
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
            logger.debug_kv("🚀  Emitted Event", event.event, "green")
            return Completed(message=success_msg)
    else:
        return Completed(message="Skipping message not directed at bot", name="SKIPPED")


app = FastAPI(lifespan=lifespan)


def get_parent_app() -> Application:
    marvin = app.state.marvin
    if not marvin:
        raise HTTPException(status_code=500, detail="Marvin instance not available")
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
    uvicorn.run(app, host="0.0.0.0", port=4200)
