import asyncio
from abc import ABC, abstractmethod

from rich.progress import track

import marvin
from marvin.models.documents import Document
from marvin.utilities.collections import batched
from marvin.utilities.types import LoggerMixin, MarvinBaseModel


class Loader(MarvinBaseModel, LoggerMixin, ABC):
    """A base class for loaders."""

    @property
    def source(self) -> str:
        return self.__class__.__name__.replace("Loader", "")

    @abstractmethod
    async def load(self) -> list[Document]:
        pass

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"

    async def load_and_store(
        self,
        topic_name: str = "marvin",
        batch_size: int = 300,
        skip_existing: bool = True,
    ) -> None:
        """Retrieve documents via subclass' load method and write them to a topic."""

        documents = await self.load()

        async with marvin.infra.chroma.Chroma(collection_name=topic_name) as chroma:
            n_documents_loaded = sum(
                [
                    await chroma.add(documents=batch, skip_existing=skip_existing)
                    for batch in batched(documents, batch_size)
                ]
            )
        self.logger.debug(
            f"saved {n_documents_loaded} documents to topic {topic_name!r}"
        )


class MultiLoader(Loader):
    loaders: list[Loader]

    async def load(self, batch_size: int = 5) -> list[Document]:
        all_documents = []
        for batch in batched(self.loaders, batch_size):
            batch_documents = await asyncio.gather(*[loader.load() for loader in batch])
            all_documents.extend(d for docs in batch_documents for d in docs)
        return all_documents

    async def load_and_store(self, topic_name: str = "marvin", batch_size: int = 5):
        for batch_of_loaders in track(
            batched(self.loaders, batch_size), description="Multi-Loading..."
        ):
            await asyncio.gather(
                *[
                    loader.load_and_store(topic_name=topic_name)
                    for loader in batch_of_loaders
                ]
            )
