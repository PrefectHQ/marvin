from typing import Literal

import chromadb

import marvin
from marvin.utilities.async_utils import run_async

_chroma_client = None


def get_client() -> chromadb.Client:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.Client()
    return _chroma_client


class Chroma:
    def __init__(self, collection: str = None):
        self.client = get_client()
        self.collection = self.client.get_or_create_collection(
            collection or marvin.settings.chroma_default_collection
        )

    async def delete(self, ids: list[str] = None, where: dict = None):
        await run_async(self.collection.delete, ids=ids, where=where)

    async def add(
        self,
        documents: list[str] = None,
        embeddings: list[list[float]] = None,
        metadatas: list[dict] = None,
        ids: list[str] = None,
    ):
        await self.collection.add(
            documents=documents, embeddings=embeddings, metadatas=metadatas, ids=ids
        )

    async def query(
        self,
        query_embeddings: list[list[float]] = None,
        query_texts: list[str] = None,
        n_results: int = 10,
        where: dict = None,
        where_document: dict = None,
        include: list[Literal["embeddings", "documents", "metadata"]] = None,
        **kwargs
    ):
        return await run_async(
            self.collection.query,
            query_embeddings=query_embeddings,
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include or [],
            **kwargs
        )

    async def get(
        self,
        ids: list[str] = None,
        where: dict = None,
        include: list[Literal["embeddings", "documents", "metadata"]] = None,
    ):
        await run_async(
            self.collection.get, ids=ids, where=where, include=include or []
        )
