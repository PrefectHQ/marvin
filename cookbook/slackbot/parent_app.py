import json

import chromadb
from chromadb import Collection, Documents, EmbeddingFunction, Embeddings
from marvin.beta.assistants import Assistant
from marvin.beta.assistants.applications import AIApplication
from marvin.tools.chroma import create_openai_embeddings
from marvin.utilities.logging import get_logger
from marvin.utilities.strings import count_tokens, slice_tokens
from prefect.events import Event, emit_event
from prefect.events.clients import PrefectCloudEventSubscriber
from prefect.events.filters import EventFilter
from websockets.exceptions import ConnectionClosedError


class OpenAIEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return [create_openai_embeddings(input)]


client = chromadb.Client()
collection: Collection = client.get_or_create_collection(
    name="parent-state",
    embedding_function=OpenAIEmbeddingFunction(),
)

logger = get_logger("PrefectEventSubscriber")

MAX_CHUNK_SIZE = 2048


def chunk_state(state: dict) -> list[str]:
    state_str = json.dumps(state)
    total_tokens = count_tokens(state_str)
    if total_tokens <= MAX_CHUNK_SIZE:
        return [state_str]
    else:
        chunks = []
        while state_str:
            chunk = slice_tokens(state_str, MAX_CHUNK_SIZE)
            chunks.append(chunk)
            state_str = state_str[len(chunk) :]
        return chunks


async def store_state_chunks(app: AIApplication, event: Event):
    state_chunks = chunk_state(app.state.read_all())
    for i, chunk in enumerate(state_chunks):
        collection.add(
            ids=[f"{event.id}-{i}"],
            documents=[chunk],
            metadatas=[{"type": "app_state"}],
        )
    logger.debug_kv("🗂️  State chunks stored", len(state_chunks), "blue")


def excerpt_from_event(event: Event) -> str:
    """Create an excerpt from the event."""
    user_name = event.payload.get("user").get("name")
    user_id = event.payload.get("user").get("id")
    user_message = event.payload.get("user_message")
    ai_response = event.payload.get("ai_response")

    return (
        f"{user_name} ({user_id}) said: {user_message}"
        f"\n\nMarvin (the assistant) responded with: {ai_response}"
    )


async def fetch_relevant_excerpt(query: str, n_results: int = 1) -> str:
    query_result = collection.query(
        query_texts=[query],
        n_results=n_results,
    )
    return "\n".join(doc for doclist in query_result["documents"] for doc in doclist)


async def update_parent_app_state(app: AIApplication, event: Event):
    relevant_excerpt = excerpt_from_event(event)
    logger.debug_kv("Retrieved child event excerpt", relevant_excerpt, "green")
    await app.default_thread.add_async(relevant_excerpt)
    logger.debug_kv("Updating parent app state", "📝", "green")
    await app.default_thread.run_async(app)


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
                    await store_state_chunks(app, event)
        except ConnectionClosedError:
            logger.debug_kv("🚨 Connection closed, reconnecting...", "red")


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
