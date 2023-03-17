import logging
from abc import ABC, abstractmethod

from pydantic import PrivateAttr

import marvin
from marvin.api.topics import update_topic
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
        """Load files from GitHub and store them in a topic."""

        digest = await self.load()

        await update_topic(topic_name, digest)

        self.logger.debug(f"wrote {digest!r} to topic {topic_name!r}")
