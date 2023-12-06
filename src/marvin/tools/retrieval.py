import asyncio
import json
import os
from typing import Optional

import httpx
from typing_extensions import Literal

import marvin

try:
    HOST, PORT = (
        marvin.settings.chroma_server_host,
        marvin.settings.chroma_server_http_port,
    )
except AttributeError:
    HOST = os.environ.get("MARVIN_CHROMA_SERVER_HOST", "localhost")
    PORT = os.environ.get("MARVIN_CHROMA_SERVER_HTTP_PORT", 8000)

QueryResultType = Literal["documents", "distances", "metadatas"]


async def create_openai_embeddings(texts: list[str]) -> list[list[float]]:
    """Create OpenAI embeddings for a list of texts."""

    try:
        import numpy  # noqa F401
    except ImportError:
        raise ImportError(
            "The numpy package is required to create OpenAI embeddings. Please install"
            " it with `pip install numpy`."
        )
    from openai import AsyncOpenAI

    return (
        (
            await AsyncOpenAI(
                api_key=marvin.settings.openai.api_key.get_secret_value()
            ).embeddings.create(
                input=[text.replace("\n", " ") for text in texts],
                model="text-embedding-ada-002",
            )
        )
        .data[0]
        .embedding
    )


async def list_collections() -> list[dict]:
    async with httpx.AsyncClient() as client:
        chroma_api_url = f"http://{HOST}:{PORT}"
        response = await client.get(
            f"{chroma_api_url}/api/v1/collections",
        )

    response.raise_for_status()
    return response.json()


async def query_chroma(
    query: str,
    collection: str = "marvin",
    n_results: int = 5,
    where: Optional[dict] = None,
    where_document: Optional[dict] = None,
    include: Optional[list[QueryResultType]] = None,
    max_characters: int = 2000,
) -> str:
    """Query Chroma.

    Example:
        User: "What are prefect blocks?"
        Assistant: >>> query_chroma("What are prefect blocks?")
    """
    query_embedding = await create_openai_embeddings([query])

    collection_ids = [
        c["id"] for c in await list_collections() if c["name"] == collection
    ]

    if len(collection_ids) == 0:
        return f"Collection {collection} not found."

    collection_id = collection_ids[0]

    async with httpx.AsyncClient() as client:
        chroma_api_url = f"http://{HOST}:{PORT}"

        response = await client.post(
            f"{chroma_api_url}/api/v1/collections/{collection_id}/query",
            data=json.dumps(
                {
                    "query_embeddings": [query_embedding],
                    "n_results": n_results,
                    "where": where or {},
                    "where_document": where_document or {},
                    "include": include or ["documents"],
                }
            ),
            headers={"Content-Type": "application/json"},
        )

    response.raise_for_status()

    return "\n".join(
        f"{i+1}. {', '.join(excerpt)}"
        for i, excerpt in enumerate(response.json()["documents"])
    )[:max_characters]


async def multi_query_chroma(
    queries: list[str],
    collection: str = "marvin",
    n_results: int = 5,
    where: Optional[dict] = None,
    where_document: Optional[dict] = None,
    include: Optional[list[QueryResultType]] = None,
    max_characters: int = 2000,
) -> str:
    """Query Chroma with multiple queries.

    Example:
        User: "What are prefect blocks and tasks?"
        Assistant: >>> multi_query_chroma(
            ["What are prefect blocks?", "What are prefect tasks?"]
        )
    """

    coros = [
        query_chroma(
            query,
            collection,
            n_results,
            where,
            where_document,
            include,
            max_characters // len(queries),
        )
        for query in queries
    ]
    return "\n".join(await asyncio.gather(*coros))[:max_characters]
