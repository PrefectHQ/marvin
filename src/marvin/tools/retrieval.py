import json
from typing import Optional

import httpx
from typing_extensions import Literal

import marvin

HOST, PORT = marvin.settings.chroma_server_host, marvin.settings.chroma_server_http_port

QueryResultType = Literal["documents", "distances", "metadatas"]


async def create_openai_embeddings(texts: list[str]) -> list[list[float]]:
    """Create OpenAI embeddings for a list of texts."""

    try:
        import numpy  # noqa F401
    except ImportError:
        raise ImportError(
            "The numpy package is required to create OpenAI embeddings. Please install"
            " it with `pip install numpy` or `pip install 'marvin[slackbot]'`."
        )
    from openai import AsyncOpenAI

    return (
        (
            await AsyncOpenAI().embeddings.create(
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
    """Query a knowledge base for documents similar to a given query.

    Args:
        query: The query to use.
        n_results: The number of results to return.

    Examples:
        >>> User: What is the meaning of life?
        >>> query_chroma("the meaning of life")
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
        [
            f"{i+1}. {', '.join(excerpt)}"
            for i, excerpt in enumerate(response.json()["documents"])
        ]
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
    """Query a knowledge base for documents similar to a set of given queries.

    Args:
        queries: The queries to use.
        n_results: The number of results to return.

    Examples:
        >>> User: What are prefect blocks and tasks?
        >>> multi_query_chroma(["prefect blocks", "prefect tasks"])
    """
    query_embeddings = await create_openai_embeddings(queries)

    collection_ids = [
        c["id"] for c in await list_collections() if c["name"] == collection
    ]

    if len(collection_ids) == 0:
        return f"Collection {collection} not found."

    collection_id = collection_ids[0]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://{HOST}:{PORT}/api/v1/collections/{collection_id}/query",
            data=json.dumps(
                {
                    "query_embeddings": [query_embeddings],
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
        [
            f"{i+1}. {', '.join(excerpt)}"
            for i, excerpt in enumerate(response.json()["documents"])
        ]
    )[:max_characters]
