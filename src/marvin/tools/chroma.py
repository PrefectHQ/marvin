import asyncio
import json
from typing import Optional

import httpx
from typing_extensions import Literal

import marvin
from marvin.tools import Tool
from marvin.utilities.embeddings import create_openai_embeddings

QueryResultType = Literal["documents", "distances", "metadatas"]


async def list_collections() -> list[dict]:
    async with httpx.AsyncClient() as client:
        chroma_api_url = f"http://{marvin.settings.chroma_server_host}:{marvin.settings.chroma_server_http_port}"
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
    query_embedding = (await create_openai_embeddings([query]))[0]

    collection_ids = [
        c["id"] for c in await list_collections() if c["name"] == collection
    ]

    if len(collection_ids) == 0:
        return f"Collection {collection} not found."

    collection_id = collection_ids[0]

    async with httpx.AsyncClient() as client:
        chroma_api_url = f"http://{marvin.settings.chroma_server_host}:{marvin.settings.chroma_server_http_port}"

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


class QueryChroma(Tool):
    """Tool for querying a Chroma index."""

    description: str = """
        Retrieve document excerpts from a knowledge-base given a query.
    """

    async def run(
        self,
        query: str,
        collection: str = "marvin",
        n_results: int = 5,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
        include: Optional[list[QueryResultType]] = None,
        max_characters: int = 2000,
    ) -> str:
        return await query_chroma(
            query, collection, n_results, where, where_document, include, max_characters
        )


class MultiQueryChroma(Tool):
    """Tool for querying a Chroma index."""

    description: str = """
        Retrieve document excerpts from a knowledge-base given a query.
    """

    async def run(
        self,
        queries: list[str],
        collection: str = "marvin",
        n_results: int = 5,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
        include: Optional[list[QueryResultType]] = None,
        max_characters: int = 2000,
        max_queries: int = 5,
    ) -> str:
        if len(queries) > max_queries:
            # make sure excerpts are not too short
            queries = queries[:max_queries]

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
        return "\n\n".join(await asyncio.gather(*coros, return_exceptions=True))
