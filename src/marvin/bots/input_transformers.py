import abc

from pydantic import Field

from marvin.utilities.types import DiscriminatingTypeModel


class InputTransformer(DiscriminatingTypeModel, abc.ABC):
    @abc.abstractmethod
    def run(self, message: str) -> str:
        pass


class PrependText(InputTransformer):
    text: str = Field(..., description="The text to prepend to the message.")

    def run(self, message: str) -> str:
        return f"{self.text} {message}"


class AppendText(InputTransformer):
    text: str = Field(..., description="The text to append to the message.")

    def run(self, message: str) -> str:
        return f"{message} {self.text}"
