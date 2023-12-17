import asyncio
import inspect
import re
from contextlib import asynccontextmanager

import uvicorn
from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Request
from jinja2 import Template
from keywords import handle_keywords
from marvin import Assistant
from marvin.beta.assistants import Thread
from marvin.beta.assistants.applications import AIApplication
from marvin.kv.json_block import JSONBlockKV
from marvin.tools.chroma import multi_query_chroma
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
    emit_assistant_completed_event,
    learn_from_child_interactions,
)
from prefect import flow, task
from prefect.states import Completed

BOT_MENTION = r"<@(\w+)>"
CACHE = TTLCache(maxsize=100, ttl=86400 * 7)
USER_MESSAGE_MAX_TOKENS = 250

parent_assistant_options = dict(
    instructions=(
        "Your job is to learn from the interactions between your child assistants and their users."
        " You will receive excerpts of these interactions as they occur."
        " Develop profiles of the users they interact with and store them in your state, using"
        " the user's name (lowercase) as the key, as shown in event excerpts you will see."
        " The user profiles (values) should include at least: {notes: list[str], n_interactions: int}."
        " Keep no more than 5 notes per user, but you may curate these over time for max utility."
        " Notes must be 3 sentences or less."
    ),
    state=JSONBlockKV(block_name="marvin-parent-app-state"),
)


def get_parent_app() -> AIApplication:
    marvin = app.state.marvin
    if not marvin:
        raise HTTPException(status_code=500, detail="Marvin instance not available")
    return marvin


async def get_notes_for_user(
    user_name: str, parent_app: AIApplication, max_tokens: int = 100
) -> str | None:
    json_notes: dict = parent_app.state.read(key=user_name)
    if inspect.iscoroutine(json_notes):
        json_notes = await json_notes

    if json_notes:
        rendered_notes = Template(
            """
            Here are some notes about {{ user_name }}:
            
            - They have interacted with {{ n_interactions }} assistants.
            Here are some notes gathered from those interactions:
            {% for note in notes %}
                - {{ note }}
            {% endfor %}
            """
        ).render(user_name=user_name, **json_notes)

        if count_tokens(rendered_notes) <= max_tokens:
            return rendered_notes
        else:
            trimmed_notes = ""
            for note in json_notes.get("notes", []):
                potential_notes = trimmed_notes + f"\n- {note}"
                if count_tokens(potential_notes) > max_tokens:
                    break
                trimmed_notes = potential_notes

            return Template(
                """
                Here are some notes about {{ user_name }}:
                
                - They have interacted with {{ n_interactions }} assistants.
                Here are some notes gathered from those interactions:\n{{ trimmed_notes }}
                """
            ).render(
                user_name=user_name,
                trimmed_notes=trimmed_notes,
                n_interactions=json_notes.get("n_interactions", 0),
            )

    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    with AIApplication(name="Marvin", **parent_assistant_options) as marvin:
        app.state.marvin = marvin
        task = asyncio.create_task(learn_from_child_interactions(marvin))
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    app.state.marvin = None


app = FastAPI(lifespan=lifespan)


@flow
async def handle_message(payload: SlackPayload) -> Completed:
    logger = get_logger("slackbot")
    user_message = (event := payload.event).text
    cleaned_message = re.sub(BOT_MENTION, "", user_message).strip()
    thread = event.thread_ts or event.ts
    if (count := count_tokens(cleaned_message)) > USER_MESSAGE_MAX_TOKENS:
        exceeded_by = count - USER_MESSAGE_MAX_TOKENS
        await task(post_slack_message)(
            message=(
                f"Your message was too long by {exceeded_by} tokens - please shorten it and try again.\n\n"
                f" For reference, here's your message at the allowed limit:\n"
                "> "
                + slice_tokens(cleaned_message, USER_MESSAGE_MAX_TOKENS).replace(
                    "\n", " "
                )
            ),
            channel_id=event.channel,
            thread_ts=thread,
        )
        return Completed(message="User message too long", name="SKIPPED")

    logger.debug_kv("Handling slack message", cleaned_message, "green")
    if (user := re.search(BOT_MENTION, user_message)) and user.group(
        1
    ) == payload.authorizations[0].user_id:
        assistant_thread = CACHE.get(thread, Thread())
        CACHE[thread] = assistant_thread

        await handle_keywords.submit(
            message=cleaned_message,
            channel_name=await get_channel_name(event.channel),
            asking_user=event.user,
            link=(
                f"{(await get_workspace_info()).get('url')}archives/"
                f"{event.channel}/p{event.ts.replace('.', '')}"
            ),
        )
        logger.info_kv(
            "Responding to", user_name := await get_user_name(event.user), "green"
        )

        with Assistant(
            name="Marvin",
            tools=[task(multi_query_chroma), task(search_github_issues)],
            instructions=(
                "You are Marvin, the paranoid android from Hitchhiker's Guide to the Galaxy."
                " Act in accordance with your character, but remember to be helpful and kind."
                " You are an expert in Python, data engineering, and software development."
                " Your primary job is to use chroma to search docs and use github to search"
                " issues and answer questions about prefect 2.x. Prefer brevity over verbosity."
                f"{await get_notes_for_user(user_name, parent_app := get_parent_app()) or ''}"
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
            event = emit_assistant_completed_event(
                child_assistant=ai,
                parent_app=parent_app,
                payload={
                    "messages": await assistant_thread.get_messages_async(
                        json_compatible=True
                    ),
                    "metadata": assistant_thread.metadata,
                    "user": user_name,
                },
            )
            logger.debug_kv("🚀  Emitted Event", event.event, "green")
            return Completed(message=success_msg)
    else:
        return Completed(message="Skipping message not directed at bot", name="SKIPPED")


@app.post("/chat")
async def chat_endpoint(request: Request):
    payload = SlackPayload(**await request.json())
    match payload.type:
        case "event_callback":
            options = dict(flow_run_name=f"respond in {payload.event.channel}")
            asyncio.create_task(handle_message.with_options(**options)(payload))
        case "url_verification":
            return {"challenge": payload.challenge}
        case _:
            raise HTTPException(400, "Invalid event type")

    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4200)
