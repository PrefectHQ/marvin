from functools import lru_cache
from typing import TYPE_CHECKING

import marvin
from marvin.config import CHROMA_INSTALLED
from marvin.models.documents import Document
from marvin.utilities.algorithms import max_marginal_relevance as mmr
from marvin.utilities.async_utils import retry_async, run_async

if TYPE_CHECKING and CHROMA_INSTALLED:
    import chromadb
    from chromadb.api.models.Collection import Collection
    from chromadb.api.types import Include, QueryResult


@lru_cache
def get_client() -> "chromadb.Client":
    import chromadb

    return chromadb.Client(marvin.settings.chroma)


async def run_async_with_retry(func, *args, **kwargs):
    return await retry_async()(run_async)(func, *args, **kwargs)


class Chroma:
    """

    A wrapper for chromadb.Client.

    If used as an async context manager, it will persist the client on exiting
    the context manager. Otherwise, it will persist on each call to `add`.

    Example:
        ```python async with Chroma() as chroma:
            await chroma.add([Document(...), ...])
        ```
    """

    def __init__(
        self,
        collection_name: str = None,
        embedding_fn=None,
    ):
        if not CHROMA_INSTALLED:
            raise ImportError(
                "Marvin tried to import chromadb, but it is not installed."
                " Marvin does not install ChromaDB by default due to"
                " the size of its dependencies, but it is required for"
                " using Marvin's knowledge features."
                " Please install it with `pip install marvin[chromadb]`"
            )
        import chromadb.utils.embedding_functions as embedding_functions

        self.client = get_client()
        self.embedding_fn = embedding_fn or embedding_functions.OpenAIEmbeddingFunction(
            api_key=marvin.settings.openai_api_key.get_secret_value()
        )
        self.collection: Collection = self.client.get_or_create_collection(
            name=collection_name or marvin.settings.default_topic,
            embedding_function=self.embedding_fn,
        )
        self._in_context = False

    async def __aenter__(self):
        self._in_context = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._in_context = False
        if marvin.settings.chroma.chroma_db_impl != "clickhouse":
            await run_async(self.client.persist)

    async def delete(
        self,
        ids: list[str] = None,
        where: dict = None,
        where_document: Document = None,
    ):
        await run_async(
            self.collection.delete,
            ids=ids,
            where=where,
            where_document=where_document,
        )

    async def delete_collection(self, collection_name: str):
        await run_async(self.client.delete_collection, collection_name=collection_name)

    async def add(
        self,
        documents: list[Document],
        skip_existing: bool = False,
    ) -> int:
        if skip_existing:
            existing_ids = set(self.collection.get(include=[])["ids"])
            document_map = {document.hash: document for document in documents}
            unique_hashes = set(document_map.keys()) - existing_ids
            documents = [document_map[hash] for hash in unique_hashes]
            if not documents:
                return 0

        await run_async_with_retry(
            self.collection.add,
            ids=[document.hash for document in documents],
            documents=[document.text for document in documents],
            metadatas=[document.metadata.dict() for document in documents],
        )

        if (
            not self._in_context
            and marvin.settings.chroma.chroma_db_impl != "clickhouse"
        ):
            await run_async(self.client.persist)
        return len(documents)

    async def query(
        self,
        query_embeddings: list[list[float]] = None,
        query_texts: list[str] = None,
        n_results: int = 10,
        where: dict = None,
        where_document: dict = None,
        include: "Include" = ["metadatas"],
        **kwargs,
    ) -> "QueryResult":
        return await run_async(
            self.collection.query,
            query_embeddings=query_embeddings,
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include,
            **kwargs,
        )

    async def count(self) -> int:
        return await run_async(self.collection.count)

    async def mmr_query(
        self,
        query: str,
        include: "Include" = ["documents", "metadatas", "embeddings"],
        **kwargs,
    ) -> "QueryResult":
        query_embedding = (await run_async(self.embedding_fn, texts=[query]))[0]

        results = await self.query(
            query_embeddings=query_embedding,
            include=include,
            **kwargs,
        )

        selected_indices = mmr(
            query_embedding=query_embedding, embedding_list=results["embeddings"][0]
        )
        return {
            field: [results[field][0][index] for index in selected_indices]
            for field in include + ["ids"]
        }
