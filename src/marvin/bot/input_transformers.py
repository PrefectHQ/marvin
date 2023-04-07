import abc

from pydantic import Field

from marvin.utilities.types import DiscriminatedUnionType


class InputTransformer(DiscriminatedUnionType, abc.ABC):
    @abc.abstractmethod
    def run(self, message: str) -> str:
        pass


class PrependText(InputTransformer):
    text: str = Field(..., description="The text to prepend to the message.")
    delimiter: str = Field(
        " ", description="The delimiter to use between the text and the message."
    )

    def run(self, message: str) -> str:
        return f"{self.text}{self.delimiter}{message}"


class AppendText(InputTransformer):
    text: str = Field(..., description="The text to append to the message.")
    delimiter: str = Field(
        " ", description="The delimiter to use between the message and the text."
    )

    def run(self, message: str) -> str:
        return f"{message}{self.delimiter}{self.text}"
