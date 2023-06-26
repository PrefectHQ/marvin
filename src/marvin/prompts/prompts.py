import abc

from pydantic import BaseModel, Field

from marvin.models.history import History
from marvin.models.messages import Message, Role


class Prompt(BaseModel, abc.ABC):
    position: int = Field(None, repr=False)

    @abc.abstractmethod
    def generate(self) -> list["Message"]:
        pass

    def __or__(self, other):
        # when the right operand is a Prompt object
        if isinstance(other, Prompt):
            return [self, other]
        # when the right operand is a list
        elif isinstance(other, list):
            return [self] + other
        else:
            raise TypeError(
                f"unsupported operand type(s) for |: '{type(self).__name__}' and"
                f" '{type(other).__name__}'"
            )

    def __ror__(self, other):
        # when the left operand is a Prompt object
        if isinstance(other, Prompt):
            return [other, self]
        # when the left operand is a list
        elif isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for |: '{type(other).__name__}' and"
                f" '{type(self).__name__}'"
            )


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
