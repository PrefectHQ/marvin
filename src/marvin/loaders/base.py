import logging
from abc import ABC, abstractmethod

from pydantic import PrivateAttr

import marvin
from marvin.documents import Document
from marvin.utilities.collections import batched
from marvin.utilities.types import MarvinBaseModel


class Loader(MarvinBaseModel, ABC):
    """A base class for loaders."""

    _logger: logging.Logger = PrivateAttr()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = marvin.get_logger(type(self).__name__)

    @property
    def logger(self):
        return self._logger

    @abstractmethod
    async def load(self):
        pass

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"

    async def load_and_store(self, topic_name: str) -> None:
        """Retrieve documents via subclass' load method and write them to a topic."""

        documents: list[Document] = await self.load()

        chroma = marvin.infra.chroma.Chroma(topic_name)

        await chroma.delete(where={"source": self.__class__.__name__})

        for batch in batched(documents, 100):
            await chroma.add(batch)

        self.logger.debug(f"saved {len(documents)} documents to topic {topic_name!r}")
