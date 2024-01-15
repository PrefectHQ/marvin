import asyncio
from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict

from marvin._rag.documents import Document
from marvin._rag.utils import batched
from marvin.utilities.logging import get_logger


class Loader(BaseModel, ABC):
    """A base class for loaders."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    @abstractmethod
    async def load(self) -> list[Document]:
        pass

    @property
    def logger(self):
        return get_logger(self.__class__.__name__)


class MultiLoader(Loader):
    loaders: list[Loader]

    async def load(self, batch_size: int = 5) -> list[Document]:
        return [
            doc
            for batch in batched(self.loaders, batch_size)
            for docs in await asyncio.gather(*(loader.load() for loader in batch))
            for doc in docs
        ]
