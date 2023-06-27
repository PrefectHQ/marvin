import inspect
from typing import Callable

from pydantic import Field

from marvin.models.history import History
from marvin.models.messages import Message, Role
from marvin.prompts.base import Prompt
from marvin.prompts.messages import MessagePrompt, System


class MessageHistory(Prompt):
    history: History
    max_messages: int = 100

    def generate(self, **kwargs) -> list[Message]:
        return self.history.get_messages(n=self.max_messages)


class Tagged(MessagePrompt):
    """
    Surround content with a tag, e.g. <b>bold</b>
    """

    tag: str
    role: Role = Role.USER

    def get_content(self) -> str:
        return f"<{self.tag}>{self.content}</{self.tag}>"


class Conditional(Prompt):
    if_: Callable = Field(
        ...,
        description=(
            "A function that returns a boolean. It will be called when the prompt is"
            " generated and provided all the variables that are passed to the render"
            " function."
        ),
    )
    if_content: str
    else_content: str
    role: Role = Role.USER
    name: str = None

    def generate(self, **kwargs) -> list[Message]:
        if self.if_(**kwargs):
            return [
                Message(
                    role=self.role,
                    content=self.render(self.if_content, render_kwargs=kwargs),
                    name=self.name,
                )
            ]
        elif self.else_content:
            return [
                Message(
                    role=self.role,
                    content=self.render(self.else_content, render_kwargs=kwargs),
                    name=self.name,
                )
            ]
        else:
            return []


class JinjaConditional(Prompt):
    if_: str = Field(
        ...,
        description=(
            "A Jinja2-compatible expression that evaluates to a boolean e.g."
            " `truthy_var` or `counter > 10`. It will automatically be templated, do"
            " not include the `{{ }}` braces."
        ),
    )
    if_content: str
    else_content: str = None
    role: Role = Role.USER
    name: str = None

    def generate(self, **kwargs) -> list[Message]:
        if_content = inspect.cleandoc(self.if_content)
        if self.else_content:
            content = (
                f"{{% if {self.if_} %}}{if_content}{{% else"
                f" %}}{inspect.cleandoc(self.else_content)}{{% endif %}}"
            )

        else:
            content = (f"{{% if {self.if_} %}}{if_content}{{% endif %}}",)
        return [
            Message(
                role=self.role,
                content=self.render(content, render_kwargs=kwargs),
                name=self.name,
            )
        ]


class ChainOfThought(Prompt):
    position: int = -1

    def generate(self, **kwargs) -> list[Message]:
        return [Message(role=Role.ASSISTANT, content="Let's think step by step.")]


class Now(System):
    content: str = "It is {{ now().strftime('%A, %d %B %Y at %I:%M:%S %p %Z') }}."
