import asyncio
from typing import Iterable, Optional

import turbopuffer as tpuf
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from turbopuffer.vectors import VectorResult

import marvin
from marvin._rag.documents import Document
from marvin._rag.utils import create_openai_embeddings

tpuf_api_key = getattr(marvin.settings, "turbopuffer_api_key", None)

if not tpuf_api_key:
    raise ValueError("Please set `MARVIN_TURBOPUFFER_API_KEY` in `~/.marvin/.env`")

tpuf.api_key = tpuf_api_key


class TurboPuffer(BaseModel):
    """Wrapper for turbopuffer.Namespace as an async context manager."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ns: tpuf.Namespace = Field(default_factory=lambda: tpuf.Namespace("marvin"))
    _in_context: bool = PrivateAttr(False)

    async def add(self, documents: Iterable[Document]) -> Iterable[Document]:
        embeddings = await asyncio.gather(
            *[create_openai_embeddings(document.text) for document in documents]
        )

        await self.upsert(
            ids=[document.id for document in documents],
            vectors=embeddings,
            attributes={
                document.id: document.metadata.model_dump(exclude_none=True)
                for document in documents
            },
        )

    async def upsert(
        self,
        ids: list[int],
        documents: Optional[Iterable[Document]] = None,
        vectors: Optional[list[list[float]]] = None,
        attributes: Optional[dict] = None,
    ):
        if documents is None and vectors is None:
            raise ValueError("Either `documents` or `vectors` must be provided.")

        if documents:
            vectors = await asyncio.gather(
                *[create_openai_embeddings(document.text) for document in documents]
            )

        self.ns.upsert(ids=ids, vectors=vectors, attributes=attributes)

    async def query(
        self,
        vector: list[float],
        top_k: int = 10,
        distance_metric: str = "cosine_distance",
        filters: Optional[dict] = None,
        include_attributes: Optional[list[str]] = None,
        include_vectors: bool = False,
    ) -> VectorResult:
        return self.ns.query(
            vector=vector,
            top_k=top_k,
            distance_metric=distance_metric,
            filters=filters,
            include_attributes=include_attributes,
            include_vectors=include_vectors,
        )

    async def delete(self, ids: list[int]):
        self.ns.delete(ids)

    async def __aenter__(self):
        self._in_context = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._in_context = False
