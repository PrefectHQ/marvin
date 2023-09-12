# This module provides tools for querying a Chroma index.
# Chroma is a knowledge-base that can be queried to retrieve document excerpts.
# The tools provided here include `QueryChroma` and `MultiQueryChroma` which allow
# for single and multiple queries respectively.

import asyncio
import json
from typing import Any, List, Optional

import httpx
from typing_extensions import Literal

from ..settings import settings
from ..utilities.embeddings import create_openai_embeddings
from . import Tool

# Define the types of query results that can be returned.
QueryResultType = Literal["documents", "distances", "metadatas"]


# Function to list all collections in the Chroma index.
async def list_collections() -> List[dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        chroma_api_url = (
            f"http://{settings.chroma_server_host}:{settings.chroma_server_http_port}"
        )
        response = await client.get(
            f"{chroma_api_url}/api/v1/collections",
        )

    response.raise_for_status()
    return response.json()


# Function to query the Chroma index.
async def query_chroma(
    query: str,
    collection: str = "marvin",
    n_results: int = 5,
    where: Optional[dict[str, Any]] = None,
    where_document: Optional[dict[str, Any]] = None,
    include: Optional[List[QueryResultType]] = None,
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
        chroma_api_url = (
            f"http://{settings.chroma_server_host}:{settings.chroma_server_http_port}"
        )

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
            ),  # type: ignore
            headers={"Content-Type": "application/json"},
        )

    response.raise_for_status()

    return "\n".join(
        [
            f"{i+1}. {', '.join(excerpt)}"
            for i, excerpt in enumerate(response.json()["documents"])
        ]
    )[:max_characters]


# Tool for querying a Chroma index.
class QueryChroma(Tool):
    """Tool for querying a Chroma index."""

    description: str = """
        Retrieve document excerpts from a knowledge-base given a query.
    """

    async def run(  # type: ignore
        self,
        query: str,
        collection: str = "marvin",
        n_results: int = 5,
        where: Optional[dict[str, Any]] = None,
        where_document: Optional[dict[str, Any]] = None,
        include: Optional[List[QueryResultType]] = None,
        max_characters: int = 2000,
    ) -> str:
        return await query_chroma(
            query, collection, n_results, where, where_document, include, max_characters
        )


# Tool for querying a Chroma index with multiple queries.
class MultiQueryChroma(Tool):
    """Tool for querying a Chroma index."""

    description: str = """
        Retrieve document excerpts from a knowledge-base given a query.
    """

    async def run(  # type: ignore
        self,
        queries: List[str],
        collection: str = "marvin",
        n_results: int = 5,
        where: Optional[dict[str, Any]] = None,
        where_document: Optional[dict[str, Any]] = None,
        include: Optional[List[QueryResultType]] = None,
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
