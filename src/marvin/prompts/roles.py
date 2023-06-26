import inspect
from typing import Literal

from marvin.models.messages import Message, Role
from marvin.prompts.base import Prompt


class MessagePrompt(Prompt):
    role: Role
    content: str
    name: str = None

    def generate(self) -> list[Message]:
        return [
            Message(
                role=self.role, content=inspect.cleandoc(self.content), name=self.name
            )
        ]


class System(MessagePrompt):
    position: int = 0
    role: Literal[Role.SYSTEM] = Role.SYSTEM


class Assistant(MessagePrompt):
    role: Literal[Role.ASSISTANT] = Role.ASSISTANT


class User(MessagePrompt):
    role: Literal[Role.USER] = Role.USER
