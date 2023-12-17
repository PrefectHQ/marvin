import json

import chromadb
from chromadb import Collection, Documents, EmbeddingFunction, Embeddings
from marvin.beta.assistants import Assistant
from marvin.beta.assistants.applications import AIApplication
from marvin.tools.retrieval import create_openai_embeddings
from marvin.utilities.logging import get_logger
from prefect.events import Event, emit_event
from prefect.events.clients import PrefectCloudEventSubscriber
from prefect.events.filters import EventFilter
from websockets.exceptions import ConnectionClosedError


class OpenAIEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return create_openai_embeddings(input)


client = chromadb.Client()
collection: Collection = client.get_or_create_collection(
    name="marvin",
    embedding_function=OpenAIEmbeddingFunction(),
)

logger = get_logger("PrefectEventSubscriber")


def excerpt_from_event(event: Event) -> str:
    """Create an excerpt from the event."""
    messages = [
        {message.get("role"): content["text"]["value"]}
        for message in event.payload["messages"]
        for content in message.get("content", [])
        if content.get("type") == "text"
        and "text" in content
        and "value" in content["text"]
    ]
    excerpt = f"{event.event}: {json.dumps(messages, indent=2)}"
    return excerpt


async def store_interaction(event: Event):
    excerpt = excerpt_from_event(event)
    collection.add(
        documents=[excerpt],
        # embeddings=[await create_openai_embeddings(excerpt)],
        metadatas=[event.payload.get("metadata", {})],
        ids=[str(event.id)],
    )


async def fetch_relevant_excerpt(query: str, n_results: int = 1) -> str:
    query_result = collection.query(
        query_texts=[query],
        # query_embeddings=[await create_openai_embeddings(query)],
        n_results=n_results,
    )
    return "\n".join(doc for doclist in query_result["documents"] for doc in doclist)


async def update_parent_app_state(app: AIApplication, event: Event):
    relevant_excerpt = await fetch_relevant_excerpt(app.instructions)
    logger.debug_kv("Retrieved child event excerpt", relevant_excerpt, "green")
    await app.default_thread.add_async(relevant_excerpt)
    logger.debug_kv("Updating parent app state", "📝", "green")
    app.default_thread.run(app)


async def learn_from_child_interactions(
    app: AIApplication, event_name: str | None = None
):
    logger.debug_kv("Starting subscriber", "👂", "green")

    if event_name is None:
        event_name = "marvin.assistants.SubAssistantRunCompleted"

    while True:
        try:
            async with PrefectCloudEventSubscriber(
                filter=EventFilter(event=dict(name=[event_name]))
            ) as subscriber:
                async for event in subscriber:
                    logger.debug_kv("Received event", event.event, "green")
                    await store_interaction(event)
                    await update_parent_app_state(app, event)
        except ConnectionClosedError:
            logger.debug_kv("🚨", "Connection closed, reconnecting...", "red")


def emit_assistant_completed_event(
    child_assistant: Assistant,
    parent_app: AIApplication,
    payload: dict,
) -> Event:
    return emit_event(
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
