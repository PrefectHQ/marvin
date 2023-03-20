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
        self, topic_name: str = "marvin", batch_size: int = 100
    ) -> None:
        """Retrieve documents via subclass' load method and write them to a topic."""

        documents = await self.load()

        chroma = marvin.infra.chroma.Chroma(topic_name)

        # TODO: add check for existing documents

        for batch in batched(documents, batch_size):
            await chroma.add(batch)

        self.logger.debug(f"saved {len(documents)} documents to topic {topic_name!r}")
