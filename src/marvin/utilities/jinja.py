"""Module for Jinja utilities."""

import inspect
import json
import os
import re
from datetime import datetime
from functools import cached_property
from typing import Any, ClassVar, Pattern, Union
from zoneinfo import ZoneInfo

from jinja2 import Environment as JinjaEnvironment
from jinja2 import StrictUndefined, select_autoescape
from jinja2 import Template as BaseTemplate
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Self

from marvin.types import BaseMessage as Message
from marvin.types import ImageFileContentBlock, TextContentBlock


class BaseEnvironment(BaseModel):
    """
    BaseEnvironment provides a configurable environment for rendering Jinja templates.

    This class encapsulates a Jinja environment with customizable global functions and
    template settings, allowing for flexible template rendering.

    Attributes:
        environment: The Jinja environment for template rendering.
        globals: A dictionary of global functions and variables available in templates.

    Example:
        Basic Usage of BaseEnvironment
        ```python
        env = BaseEnvironment()

        rendered = env.render("Hello, {{ name }}!", name="World")
        print(rendered)  # Output: Hello, World!

        ```
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    environment: JinjaEnvironment = Field(
        default=JinjaEnvironment(
            autoescape=select_autoescape(default_for_string=False),
            trim_blocks=True,
            lstrip_blocks=True,
            auto_reload=True,
            undefined=StrictUndefined,
        )
    )

    globals: dict[str, Any] = Field(
        default_factory=lambda: {
            "now": lambda: datetime.now(ZoneInfo("UTC")),
            "inspect": inspect,
            "getcwd": os.getcwd,
        }
    )

    @model_validator(mode="after")
    def setup_globals(self: Self) -> Self:
        self.environment.globals.update(self.globals)  # type: ignore
        return self

    def render(self, template: Union[str, BaseTemplate], **kwargs: Any) -> str:
        """Renders a given template `str` or `BaseTemplate` with provided context.

        Args:
            template: The template to be rendered.
            **kwargs: Context variables to be passed to the template.

        Returns:
            The rendered template as a string.

        Example:
            Basic Usage of `BaseEnvironment.render`
            ```python
            from marvin.utilities.jinja import Environment as jinja_env

            rendered = jinja_env.render("Hello, {{ name }}!", name="World")
            print(rendered) # Output: Hello, World!
            ```
        """
        if isinstance(template, str):
            return self.environment.from_string(template).render(**kwargs)
        return template.render(**kwargs).strip()


Environment = BaseEnvironment()


def split_text_by_tokens(
    text: str, split_tokens: list[str], only_on_newline: bool = True
) -> list[tuple[str, str]]:
    """
    Splits a given text by a list of tokens.

    Args:
        text: The text to be split. split_tokens: The tokens to split the text
        by. only_on_newline: If True, only match tokens that are either
        immediately following a newline or are the first item in the text.

    Returns:
        A list of tuples containing the token and the text following it.

    Example:
        Basic Usage of `split_text_by_tokens` ```python from
        marvin.utilities.jinja import split_text_by_tokens

        text = "Hello, World!" split_tokens = ["Hello", "World"] pairs =
        split_text_by_tokens(text, split_tokens) print(pairs) # Output:
        [("Hello", ", "), ("World", "!")] ```
    """
    cleaned_text = inspect.cleandoc(text)

    # Find all positions of tokens in the text
    positions = [
        (match.start(), match.end(), match.group().rstrip(":").strip())
        for token in split_tokens
        for match in re.finditer(
            (r"(^|\n\s*)" if only_on_newline else "") + re.escape(token) + r"(?::\s*)?",
            cleaned_text,
        )
    ]

    # Sort positions by their start index
    positions.sort(key=lambda x: x[0])

    paired: list[tuple[str, str]] = []
    prev_end = 0
    prev_token = split_tokens[0]
    for start, end, token in positions:
        paired.append((prev_token, cleaned_text[prev_end:start].strip()))
        prev_end = end
        prev_token = token

    paired.append((prev_token, cleaned_text[prev_end:].strip()))

    # Remove pairs where the text is empty
    paired = [(token.replace(":", ""), text) for token, text in paired if text]

    return paired


class Transcript(BaseModel):
    """
    A Transcript is a model that represents a conversation involving multiple
    roles as a single string. It can be parsed into discrete JSON messages.

    Transcripts contain special tokens that indicate how to split the transcript
    into discrete messages.

    The first special token type indicates the message `role`. Default roles are
    `|SYSTEM|`, `|HUMAN|`, `|USER|`, and `|ASSISTANT|`. When these tokens appear
    at the start of a newline, all text following the token until the next
    newline or token is considered part of the message with the given role.

    The second special token type indicates the message `type`. By default, messages all have the `text` type. By supplying a token like `|IMAGE|`, you can indicate that a portion of the message is an image. Use `|TEXT|` to end the image portion and return to text. An

    Attributes:
        content: The content of the transcript.
        roles: The roles involved in the transcript.
        environment: The jinja environment to use for rendering the transcript.

    Example:
        Basic Usage of Transcript:
        ```python
        from marvin.utilities.jinja import Transcript

        transcript = Transcript(
            content="|SYSTEM| Hello, there!\n\n|USER| Hello, yourself!",
            roles={"|SYSTEM|": "system", "|USER|": "user"},
        )
        print(transcript.render_to_messages())
        # [
        #   BaseMessage(content='system: Hello, there!', role='system'),
        #   BaseMessage(content='Hello, yourself!', role='user')
        # ]
        ```
    """

    content: str
    roles: dict[str, str] = Field(
        default={
            "|SYSTEM|": "system",
            "|HUMAN|": "user",
            "|USER|": "user",
            "|ASSISTANT|": "assistant",
        }
    )
    types: dict[str, str] = Field(
        default={
            "|IMAGE|": "image",
            "|TEXT|": "text",
        }
    )
    environment: ClassVar[BaseEnvironment] = Environment

    @field_validator("roles", "types")
    def _check_trailing_colons(cls, dct):
        for key in dct:
            if key.endswith(":"):
                raise ValueError(f"'{key}' should not end with a colon.")
        return dct

    @cached_property
    def role_regex(self) -> Pattern[str]:
        return re.compile("|".join([f"(^|\n){role}" for role in self.roles]))

    @cached_property
    def type_regex(self) -> Pattern[str]:
        return re.compile("|".join([f"(^|\n){type_}" for type_ in self.types]))

    def render(self: Self, **kwargs: Any) -> str:
        return self.environment.render(self.content, **kwargs)

    def render_to_messages(
        self: Self,
        **kwargs: Any,
    ) -> list[Message]:
        pairs = split_text_by_tokens(
            text=self.render(**kwargs).strip(),
            split_tokens=[f"{key}" for key in (list(self.roles) + list(self.types))],
            only_on_newline=True,
        )

        messages = []

        role = "system"
        message_content = []

        # iterate over every pair of token and content, accumlating content for
        # each role. When the role changes, we create a new message containing
        # the accumulated content
        for pair in pairs:
            token = pair[0].strip()
            content = pair[1]

            # if the token indicates a role, this is a new message, so "post"
            # the previous message and start accumulating content
            if token in self.roles:
                if message_content:
                    messages.append(Message(role=role, content=message_content))
                    message_content.clear()
                role = self.roles[token]

            content_type = self.types.get(token, "text")
            if content_type == "text":
                message_content.append(TextContentBlock(text=content))
            else:
                message_content.append(
                    ImageFileContentBlock(image_url=json.loads(content))
                )

        if message_content:
            messages.append(Message(role=role, content=message_content))

        return messages
