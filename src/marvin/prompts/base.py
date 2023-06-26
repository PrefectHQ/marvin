import abc

from pydantic import BaseModel, Field

from marvin.models.messages import Message


class Prompt(BaseModel, abc.ABC):
    position: int = Field(None, repr=False)

    @abc.abstractmethod
    def generate(self) -> list["Message"]:
        pass

    def __or__(self, other):
        """
        Supports pipe syntax:
        prompt = (
            Prompt()
            | Prompt()
            | Prompt()
        )
        """
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
        """
        Supports pipe syntax:
        prompt = (
            Prompt()
            | Prompt()
            | Prompt()
        )
        """
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
