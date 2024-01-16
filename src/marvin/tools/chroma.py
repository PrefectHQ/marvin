import asyncio
import os
import uuid
from typing import Any, Literal, Optional, Union

try:
    from chromadb import (
        Client,
        Documents,
        EmbeddingFunction,
        Embeddings,
        GetResult,
        HttpClient,
    )
except ImportError:
    raise ImportError(
        "The chromadb package is required to query Chroma. Please install"
        " it with `pip install chromadb` or `pip install marvin[chroma]`."
    )


import marvin
from marvin._rag.utils import create_openai_embeddings
from marvin.utilities.asyncio import run_sync

QueryResultType = Literal["documents", "distances", "metadatas"]


try:
    HOST, PORT = (
        getattr(marvin.settings, "chroma_server_host"),
        getattr(marvin.settings, "chroma_server_http_port"),
    )
    DEFAULT_COLLECTION_NAME = getattr(
        marvin.settings, "chroma_default_collection_name", "marvin"
    )
except AttributeError:
    HOST = os.environ.get("MARVIN_CHROMA_SERVER_HOST", "localhost")  # type: ignore
    PORT = os.environ.get("MARVIN_CHROMA_SERVER_HTTP_PORT", 8000)  # type: ignore
    DEFAULT_COLLECTION_NAME = os.environ.get(
        "MARVIN_CHROMA_DEFAULT_COLLECTION_NAME", "marvin"
    )


def get_client(
    client_type: Literal["http", "base"] = "base", **kwargs: Any
) -> Union[Client, HttpClient]:
    if client_type == "base":
        return Client(**kwargs)
    elif client_type == "http":
        return HttpClient(host=HOST, port=PORT, **kwargs)
    else:
        raise ValueError("client_type must be one of 'base' or 'http'.")


class OpenAIEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return [run_sync(create_openai_embeddings(input))]


async def query_chroma(
    query: str,
    collection: str = "marvin",
    n_results: int = 5,
    where: Optional[dict[str, Any]] = None,
    where_document: Optional[dict[str, Any]] = None,
    include: Optional[list[QueryResultType]] = None,
    max_characters: int = 2000,
) -> str:
    """Query a collection of document excerpts for a query.

    Example:
        User: "What are prefect blocks?"
        Assistant: >>> query_chroma("What are prefect blocks?")
    """
    client = get_client(client_type="http")
    collection_object = client.get_or_create_collection(
        name=collection or DEFAULT_COLLECTION_NAME,
        embedding_function=OpenAIEmbeddingFunction(),
    )
    query_result = collection_object.query(
        query_texts=[query],
        n_results=n_results,
        where=where,
        where_document=where_document,
        include=include or ["documents"],
    )
    return "".join(doc for doclist in query_result["documents"] for doc in doclist)[
        :max_characters
    ]


async def multi_query_chroma(
    queries: list[str],
    collection: str = "marvin",
    n_results: int = 5,
    where: Optional[dict[str, Any]] = None,
    where_document: Optional[dict[str, Any]] = None,
    include: Optional[list[QueryResultType]] = None,
    max_characters: int = 2000,
) -> str:
    """Retrieve excerpts to aid in answering multifacted questions.

    Example:
        User: "What are prefect blocks and tasks?"
        Assistant: >>> multi_query_chroma(
            ["What are prefect blocks?", "What are prefect tasks?"]
        )
        multi_query_chroma -> document excerpts explaining both blocks and tasks
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


def store_document(
    document: str, metadata: dict[str, Any], collection_name: str = "glacial"
) -> GetResult:
    """Store a document in Chroma for future reference.

    Args:
        document: The document to store.
        metadata: The metadata to store with the document.

    Returns:
        The stored document.
    """
    client = get_client(client_type="http")

    collection = client.get_or_create_collection(
        name=collection_name, embedding_function=OpenAIEmbeddingFunction()
    )
    doc_id = metadata.get("msg_id", str(uuid.uuid4()))

    collection.add(
        ids=[doc_id],
        documents=[document],
        metadatas=[metadata],
    )

    return collection.get(ids=doc_id)
