import re
from typing import Any, Iterable, Literal, Optional

from chromadb.api.models.Collection import Collection
from chromadb.api.types import Include, QueryResult
from prefect.utilities.collections import distinct
from pydantic import BaseModel, Field, model_validator

import marvin
from marvin._rag.documents import Document
from marvin.tools.chroma import OpenAIEmbeddingFunction, get_client
from marvin.utilities.asyncio import run_async


def get_distinct_documents(documents: Iterable[Document]) -> Iterable[Document]:
    """Return a list of distinct documents."""
    return distinct(documents, key=lambda doc: doc.hash)


class Chroma(BaseModel):
    """A wrapper for chromadb.Client - used as an async context manager"""

    client_type: Literal["base", "http"] = "base"
    embedding_fn: Any = Field(default_factory=OpenAIEmbeddingFunction)
    collection: Optional[Collection] = None

    _in_context: bool = False

    @model_validator(mode="after")
    def validate_collection(self):
        if not self.collection:
            client = get_client(self.client_type)
            self.collection = client.get_or_create_collection(
                name="marvin", embedding_function=self.embedding_fn
            )
        return self

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

    async def add(self, documents: list[Document]) -> Iterable[Document]:
        documents = get_distinct_documents(documents)
        kwargs = dict(
            ids=[document.id for document in documents],
            documents=[document.text for document in documents],
            metadatas=[
                document.metadata.model_dump(exclude_none=True) or None
                for document in documents
            ],
            embeddings=[document.embedding or [] for document in documents],
        )

        await run_async(self.collection.add, **kwargs)

        get_result = await run_async(self.collection.get, ids=kwargs["ids"])

        return get_result.get("documents")

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

    async def upsert(self, documents: list[Document]):
        documents = get_distinct_documents(documents)
        kwargs = dict(
            ids=[document.id for document in documents],
            documents=[document.text for document in documents],
            metadatas=[
                document.metadata.model_dump(exclude_none=True) or None
                for document in documents
            ],
            embeddings=[document.embedding or [] for document in documents],
        )
        await run_async(self.collection.upsert, **kwargs)

        get_result = await run_async(self.collection.get, ids=kwargs["ids"])

        return get_result.get("documents")

    async def reset_collection(self):
        """Delete and recreate the collection."""
        client = get_client(self.client_type)
        await run_async(client.delete_collection, self.collection.name)
        self.collection = await run_async(
            client.create_collection,
            name=self.collection.name,
            embedding_function=self.embedding_fn,
        )

    def ok(self) -> bool:
        logger = marvin.utilities.logging.get_logger()
        try:
            version = self.client.get_version()
        except Exception as e:
            logger.error(f"Cannot connect to Chroma: {e}")
        if re.match(r"^\d+\.\d+\.\d+$", version):
            logger.debug(f"Connected to Chroma v{version}")
            return True
        return False

    async def __aenter__(self):
        self._in_context = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._in_context = False
