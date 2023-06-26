from marvin.models.history import History
from marvin.models.messages import Message, Role
from marvin.prompts.base import Prompt


class MessageHistory(Prompt):
    history: History
    max_messages: int = 100

    def generate(self) -> list[Message]:
        return self.history.get_messages(n=self.max_messages)


class ChainOfThought(Prompt):
    position: int = -1

    def generate(self) -> list[Message]:
        return [Message(role=Role.ASSISTANT, content="Let's think step by step.")]
