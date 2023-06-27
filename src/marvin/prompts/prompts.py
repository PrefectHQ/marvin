from pydantic import Field

from marvin.models.history import History
from marvin.models.messages import Message, Role
from marvin.prompts.base import Prompt
from marvin.prompts.messages import MessagePrompt, System


class MessageHistory(Prompt):
    history: History
    max_messages: int = 100

    def generate(self) -> list[Message]:
        return self.history.get_messages(n=self.max_messages)


class Tagged(MessagePrompt):
    """
    Surround content with a tag, e.g. <b>bold</b>
    """

    tag: str
    role: Role = Role.USER

    def get_content(self) -> str:
        return f"<{self.tag}>{self.content}</{self.tag}>"


class Conditional(MessagePrompt):
    condition: str = Field(
        ...,
        description=(
            "A Jinja2-compatible expression that evaluates to a boolean e.g."
            " `truthy_var` or `counter > 10`. It will automatically be templated, do"
            " not include the `{{ }}`."
        ),
    )
    role: Role = Role.USER

    def get_content(self) -> str:
        return f"{{% if {self.condition} %}}{self.content}{{% endif %}}"


class ChainOfThought(Prompt):
    position: int = -1

    def generate(self) -> list[Message]:
        return [Message(role=Role.ASSISTANT, content="Let's think step by step.")]


class Now(System):
    content: str = "It is {{ now().strftime('%A, %d %B %Y at %I:%M:%S %p %Z') }}."
