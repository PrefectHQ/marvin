import chromadb
import chromadb.config
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Include, QueryResult
from chromadb.utils import embedding_functions

import marvin
from marvin.models.documents import Document
from marvin.utilities.async_utils import run_async


def get_client(settings: chromadb.config.Settings = None) -> chromadb.Client:
    return chromadb.Client(settings=settings or marvin.settings.chroma)


class Chroma:
    def __init__(
        self,
        collection_name: str = None,
        settings: chromadb.config.Settings = None,
    ):
        self.client = get_client(settings=settings)
        self.collection: Collection = self.client.get_or_create_collection(
            name=collection_name or marvin.settings.default_topic,
            embedding_function=embedding_functions.OpenAIEmbeddingFunction(
                api_key=marvin.settings.openai_api_key.get_secret_value()
            ),
        )

    async def delete(self, ids: list[str] = None, where: dict = None):
        await run_async(self.collection.delete, ids=ids, where=where)

    async def delete_collection(self, collection_name: str):
        await run_async(self.client.delete_collection, collection_name=collection_name)

    async def add(
        self,
        documents: list[Document],
    ):
        await run_async(
            self.collection.add,
            ids=[document.id for document in documents],
            documents=[document.text for document in documents],
            metadatas=[document.metadata for document in documents],
        )
        await run_async(self.client.persist)

    async def query(
        self,
        query_embeddings: list[list[float]] = None,
        query_texts: list[str] = None,
        n_results: int = 10,
        where: dict = None,
        where_document: dict = None,
        include: Include = ["metadatas"],
        **kwargs
    ) -> QueryResult:
        return await run_async(
            self.collection.query,
            query_embeddings=query_embeddings,
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include,
            **kwargs
        )

    async def get(
        self,
        ids: list[str] = None,
        where: dict = None,
        include: Include = None,
    ):
        await run_async(
            self.collection.get, ids=ids, where=where, include=include or []
        )
