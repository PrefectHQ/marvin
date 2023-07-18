import inspect
from typing import Callable, Literal

from pydantic import Field

from marvin.prompts.base import Prompt
from marvin.utilities.history import History, HistoryFilter
from marvin.utilities.messages import Message, Role


class MessagePrompt(Prompt):
    role: Role
    content: str = Field(
        ..., description="The message content, which can be a Jinja2 template"
    )
    name: str = None
    priority: int = 2

    def get_content(self) -> str:
        """
        Override this method to easily customize behavior
        """
        return self.content

    def generate(self, **kwargs) -> list[Message]:
        return [
            Message(
                role=self.role,
                content=self.render(
                    self.get_content(),
                    render_kwargs={
                        **self.dict(exclude={"role", "content", "name", "priority"}),
                        **kwargs,
                    },
                ),
                name=self.name,
            )
        ]

    def read(self, **kwargs) -> str:
        return self.render(
            self.get_content(),
            render_kwargs={
                **self.dict(exclude={"role", "content", "name", "priority"}),
                **kwargs,
            },
        )

    def __init__(self, content: str = None, *args, **kwargs):
        content = kwargs.get("content", content)
        super().__init__(
            *args, **{**kwargs, **({"content": content} if content else {})}
        )


class System(MessagePrompt):
    position: int = 0
    priority: int = 1
    role: Literal[Role.SYSTEM] = Role.SYSTEM


class Assistant(MessagePrompt):
    role: Literal[Role.ASSISTANT] = Role.ASSISTANT


class User(MessagePrompt):
    role: Literal[Role.USER] = Role.USER


class MessageHistory(Prompt):
    history: History
    n: int = 100
    skip: int = None
    filter: HistoryFilter = None

    def generate(self, **kwargs) -> list[Message]:
        return self.history.get_messages(n=self.n, skip=self.skip, filter=self.filter)


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
