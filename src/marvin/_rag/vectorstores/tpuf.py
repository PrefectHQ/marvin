import asyncio
import os
from typing import Iterable, Optional, Union

import turbopuffer as tpuf
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ImportString,
    PrivateAttr,
    SecretStr,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from turbopuffer.vectors import VectorResult

from marvin._rag.documents import Document
from marvin._rag.utils import create_openai_embeddings


class TurboPufferSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MARVIN_TURBOPUFFER_",
        env_file="" if os.getenv("MARVIN_TEST_MODE") else ("~/.marvin/.env", ".env"),
        extra="allow",
        arbitrary_types_allowed=True,
    )

    api_key: SecretStr
    namespace: str = "marvin"
    fetch_document_fn: ImportString = "marvin._rag.utils.fetch_documents_from_gcs"

    @model_validator(mode="after")
    def set_api_key(self):
        tpuf.api_key = self.api_key.get_secret_value()


tpuf_settings = TurboPufferSettings()


class TurboPuffer(BaseModel):
    """Wrapper for turbopuffer.Namespace as an async context manager."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ns: tpuf.Namespace = Field(
        default_factory=lambda: tpuf.Namespace(tpuf_settings.namespace)
    )
    _in_context: bool = PrivateAttr(False)

    async def upsert(
        self,
        documents: Optional[Iterable[Document]] = None,
        ids: Optional[Union[list[str], list[int]]] = None,
        vectors: Optional[list[list[float]]] = None,
        attributes: Optional[dict] = None,
    ):
        if documents is None and vectors is None:
            raise ValueError("Either `documents` or `vectors` must be provided.")

        if documents:
            ids = [document.id for document in documents]
            vectors = await asyncio.gather(
                *[create_openai_embeddings(document.text) for document in documents]
            )

        self.ns.upsert(ids=ids, vectors=vectors, attributes=attributes)

    async def query(
        self,
        text: Optional[str] = None,
        vector: Optional[list[float]] = None,
        top_k: int = 10,
        distance_metric: str = "cosine_distance",
        filters: Optional[dict] = None,
        include_attributes: Optional[list[str]] = None,
        include_vectors: bool = False,
    ) -> VectorResult:
        if text:
            vector = await create_openai_embeddings(text)
        else:
            if vector is None:
                raise ValueError("Either `text` or `vector` must be provided.")

        return self.ns.query(
            vector=vector,
            top_k=top_k,
            distance_metric=distance_metric,
            filters=filters,
            include_attributes=include_attributes,
            include_vectors=include_vectors,
        )

    async def delete(self, ids: Union[str, int, list[str], list[int]]):
        self.ns.delete(ids)

    async def __aenter__(self):
        self._in_context = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._in_context = False
