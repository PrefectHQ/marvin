import asyncio
import os
from typing import TYPE_CHECKING, Any, Optional

try:
    from chromadb import Documents, EmbeddingFunction, Embeddings, HttpClient
except ImportError:
    raise ImportError(
        "The chromadb package is required to query Chroma. Please install"
        " it with `pip install chromadb` or `pip install marvin[chroma]`."
    )


from typing_extensions import Literal

import marvin

if TYPE_CHECKING:
    from openai.types import CreateEmbeddingResponse

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


def create_openai_embeddings(texts: list[str]) -> list[float]:
    """Create OpenAI embeddings for a list of texts."""

    try:
        import numpy  # noqa F401 # type: ignore
    except ImportError:
        raise ImportError(
            "The numpy package is required to create OpenAI embeddings. Please install"
            " it with `pip install numpy`."
        )
    from marvin.client.openai import MarvinClient

    embedding: "CreateEmbeddingResponse" = MarvinClient().client.embeddings.create(
        input=[text.replace("\n", " ") for text in texts],
        model="text-embedding-ada-002",
    )

    return embedding.data[0].embedding


class OpenAIEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return [create_openai_embeddings(input)]


client = HttpClient(host=HOST, port=PORT)


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
