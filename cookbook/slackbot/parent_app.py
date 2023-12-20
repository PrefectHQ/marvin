import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from marvin import ai_fn
from marvin.beta.assistants import Assistant
from marvin.beta.assistants.applications import AIApplication
from marvin.kv.json_block import JSONBlockKV
from marvin.utilities.logging import get_logger
from prefect.events import Event, emit_event
from prefect.events.clients import PrefectCloudEventSubscriber
from prefect.events.filters import EventFilter
from pydantic import confloat
from typing_extensions import TypedDict
from websockets.exceptions import ConnectionClosedError

PARENT_APP_STATE_BLOCK_NAME = "marvin-parent-app-state"
PARENT_APP_STATE = JSONBlockKV(block_name=PARENT_APP_STATE_BLOCK_NAME)


class Lesson(TypedDict):
    relevance: confloat(ge=0, le=1)
    heuristic: str | None


@ai_fn(model="gpt-3.5-turbo-1106")
def take_lesson_from_interaction(
    transcript: str,
    assistant_instructions: str,
    observer_role: str = "data architect",
    irrelevant_topics: str = "Anything not related to data engineering",
) -> Lesson:
    """You are an expert {{ observer_role }}, and you are counseling an AI assistant named Marvin.

    {{ irrelevant_topics }} is not relevant to Marvin's purpose, and has 0 relevance.

    Here is the transcript of an interaction between Marvin and a user:
    {{ transcript }}

    ... and here is the stated purpose of the assistant:
    {{ assistant_instructions }}

    how directly relevant to the assistant's purpose is this interaction?
    - if not at all, relevance = 0 & heuristic = None. (most commonly, this will be the case)
    - if very, relevance >= 0.5, <1 & heuristic = "1 SHORT SENTENCE (max) summary of a generalizable lesson".
    """


logger = get_logger("PrefectEventSubscriber")


def excerpt_from_event(event: Event) -> str:
    """Create an excerpt from the event - TODO jinja this"""
    user_name = event.payload.get("user").get("name")
    user_id = event.payload.get("user").get("id")
    user_message = event.payload.get("user_message")
    ai_response = event.payload.get("ai_response")

    return (
        f"{user_name} ({user_id}) said: {user_message}"
        f"\n\nMarvin (the assistant) responded with: {ai_response}"
    )


async def update_parent_app_state(app: AIApplication, event: Event):
    event_excerpt = excerpt_from_event(event)
    lesson = take_lesson_from_interaction(
        event_excerpt, event.payload.get("ai_instructions").split("START_USER_NOTES")[0]
    )
    if lesson["relevance"] >= 0.5 and lesson["heuristic"] is not None:
        experience = (
            f"transcript:\n\n{event_excerpt}\n\nlesson: {lesson['heuristic']!r}"
        )
        logger.debug_kv("💡 Learned lesson from excerpt", experience, "green")
        await app.default_thread.add_async(experience)
        logger.debug_kv("📝", "Updating parent app state", "green")
        await app.default_thread.run_async(app)
    else:
        logger.debug_kv("🥱 ", "nothing special", "green")
        user_id = event.payload.get("user").get("id")
        current_user_state = app.state.read(user_id) or dict(
            name=event.payload.get("user").get("name"),
            n_interactions=0,
        )
        current_user_state["n_interactions"] += 1
        app.state.write(user_id, state := current_user_state)
        logger.debug_kv(
            f"📋 Updated state for user {user_id} to", json.dumps(state), "green"
        )


async def learn_from_child_interactions(
    app: AIApplication, event_name: str | None = None
):
    if event_name is None:
        event_name = "marvin.assistants.SubAssistantRunCompleted"

    logger.debug_kv("👂 Listening for", event_name, "green")
    while not sum(map(ord, "vogon poetry")) == 42:
        try:
            async with PrefectCloudEventSubscriber(
                filter=EventFilter(event=dict(name=[event_name]))
            ) as subscriber:
                async for event in subscriber:
                    logger.debug_kv("📬 Received event", event.event, "green")
                    await update_parent_app_state(app, event)
        except Exception as e:
            if isinstance(e, ConnectionClosedError):
                logger.debug_kv("🚨 Connection closed, reconnecting...", "red")
            else:
                logger.debug_kv("🚨", str(e), "red")
                raise e


parent_assistant_options = dict(
    instructions=(
        "Your job is learn from the interactions of data engineers (users) and Marvin (a growing AI assistant)."
        " You'll receive excerpts of these interactions (which are in the Prefect Slack workspace) as they occur."
        " Your notes will be provided to Marvin when it interacts with users. Notes should be stored for each user"
        " with the user's id as the key. The user id will be shown in the excerpt of the interaction."
        " The user profiles (values) should include at least: {name: str, notes: list[str], n_interactions: int}."
        " Keep NO MORE THAN 3 notes per user, but you may curate/update these over time for Marvin's maximum benefit."
        " Notes must be 2 sentences or less, must be concise and use inline markdown formatting for code and links."
        " Each note should be a concrete and TECHNICAL observation related to the user's data engineering needs."
    ),
    state=PARENT_APP_STATE,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with AIApplication(name="Marvin", **parent_assistant_options) as marvin:
        app.state.marvin = marvin
        task = asyncio.create_task(learn_from_child_interactions(marvin))
        yield
        task.cancel()
        try:
            await task
        except asyncio.exceptions.CancelledError:
            get_logger("PrefectEventSubscriber").debug_kv(
                "👋", "Stopped listening for child events", "red"
            )

    app.state.marvin = None


def emit_assistant_completed_event(
    child_assistant: Assistant, parent_app: AIApplication, payload: dict
) -> Event:
    event = emit_event(
        event="marvin.assistants.SubAssistantRunCompleted",
        resource={
            "prefect.resource.id": child_assistant.id,
            "prefect.resource.name": "child assistant",
            "prefect.resource.role": "assistant",
        },
        related=[
            {
                "prefect.resource.id": parent_app.id,
                "prefect.resource.name": "parent assistant",
                "prefect.resource.role": "assistant",
            }
        ],
        payload=payload,
    )
    return event
