import abc
from typing import Callable, Optional

from marvin.utilities.messages import Message
from marvin.utilities.types import MarvinBaseModel


class StreamHandler(MarvinBaseModel, abc.ABC):
    callback: Optional[Callable] = None

    @abc.abstractmethod
    def handle_streaming_response(self, api_response) -> Message:
        raise NotImplementedError()
