import logging
from abc import ABC, abstractmethod

from pydantic import PrivateAttr

import marvin
from marvin.client import MarvinClient
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

    async def load_and_store(self, topic_name: str, **client_kwargs) -> None:
        """Load files from GitHub and store them in a topic."""

        digest = await self.load()

        async with MarvinClient(**client_kwargs) as client:
            await client.write_to_topic(topic_name, digest)

        self.logger.debug(f"wrote {digest!r} to topic {topic_name!r}")
