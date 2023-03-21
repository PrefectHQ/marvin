from abc import ABC, abstractmethod

import marvin
from marvin.models.documents import Document
from marvin.utilities.collections import batched
from marvin.utilities.types import LoggerMixin, MarvinBaseModel


class Loader(MarvinBaseModel, LoggerMixin, ABC):
    """A base class for loaders."""

    @abstractmethod
    async def load(self) -> list[Document]:
        pass

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"

    async def load_and_store(
        self,
        topic_name: str = "marvin",
        batch_size: int = 100,
        skip_existing: bool = True,
    ) -> None:
        """Retrieve documents via subclass' load method and write them to a topic."""

        documents = await self.load()

        chroma = marvin.infra.chroma.Chroma(topic_name)

        n_documents_loaded = 0

        for batch in batched(documents, batch_size):
            n_documents_loaded += await chroma.add(batch, skip_existing=skip_existing)

        self.logger.debug(
            f"saved {n_documents_loaded} documents to topic {topic_name!r}"
        )
