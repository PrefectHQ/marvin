import abc

from pydantic import BaseModel

from marvin.models import Message, Role
from marvin.models.history import History


class Prompt(BaseModel, abc.ABC):
    position: int = None

    @abc.abstractmethod
    def generate(self) -> list["Message"]:
        pass


class MessageHistory(Prompt):
    history: History
    max_messages: int = 100

    def generate(self) -> list[Message]:
        return self.history.get_messages(n=self.max_messages)


class System(Prompt):
    position: int = 0
    template: str

    def generate(self) -> list[Message]:
        return [Message(role=Role.SYSTEM, content=self.template)]


class ChainOfThought(Prompt):
    position: int = -1

    def generate(self) -> list[Message]:
        return [Message(role=Role.ASSISTANT, content="Let's think step by step")]
