from typing import Literal

from pydantic import Field

from marvin.models.messages import Message, Role
from marvin.prompts.base import Prompt


class MessagePrompt(Prompt):
    role: Role
    content: str = Field(
        ..., description="The message content, which can be a Jinja2 template"
    )
    name: str = None

    def get_content(self) -> str:
        """
        Override this method to easily customize behavior
        """
        return self.content

    def generate(self, **kwargs) -> list[Message]:
        return [
            Message(
                role=self.role,
                content=self.render(self.get_content(), render_kwargs=kwargs),
                name=self.name,
            )
        ]


class System(MessagePrompt):
    position: int = 0
    role: Literal[Role.SYSTEM] = Role.SYSTEM


class Assistant(MessagePrompt):
    role: Literal[Role.ASSISTANT] = Role.ASSISTANT


class User(MessagePrompt):
    role: Literal[Role.USER] = Role.USER
