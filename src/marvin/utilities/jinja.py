"""Module for Jinja utilities."""
import inspect
import re
from datetime import datetime
from typing import Any, ClassVar, Pattern, Union
from zoneinfo import ZoneInfo

from jinja2 import Environment as JinjaEnvironment
from jinja2 import StrictUndefined, select_autoescape
from jinja2 import Template as BaseTemplate
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from marvin.requests import BaseMessage as Message


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
        return template.render(**kwargs)


Environment = BaseEnvironment()


def split_text_by_tokens(text: str, split_tokens: list[str]) -> list[tuple[str, str]]:
    """
    Splits a given text by a list of tokens.

    Args:
        text: The text to be split.
        split_tokens: The tokens to split the text by.

    Returns:
        A list of tuples containing the token and the text following it.

    Example:
        Basic Usage of `split_text_by_tokens`
        ```python
        from marvin.utilities.jinja import split_text_by_tokens

        text = "Hello, World!"
        split_tokens = ["Hello", "World"]
        pairs = split_text_by_tokens(text, split_tokens)
        print(pairs) # Output: [("Hello", ", "), ("World", "!")]
        ```
    """
    cleaned_text = inspect.cleandoc(text)

    # Find all positions of tokens in the text
    positions = [
        (match.start(), match.end(), match.group().rstrip(":").strip())
        for token in split_tokens
        for match in re.finditer(re.escape(token) + r"(?::\s*)?", cleaned_text)
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
    """Transcript is a model representing a conversation involving multiple roles.

    Attributes:
        content: The content of the transcript.
        roles: The roles involved in the transcript.
        environment: The jinja environment to use for rendering the transcript.

    Example:
        Basic Usage of Transcript:
        ```python
        from marvin.utilities.jinja import Transcript

        transcript = Transcript(
            content="system: Hello, there! user: Hello, yourself!",
            roles=["system", "user"],
        )
        print(transcript.render_to_messages())
        # [
        #   BaseMessage(content='system: Hello, there!', role='system'),
        #   BaseMessage(content='Hello, yourself!', role='user')
        # ]
        ```
    """

    content: str
    roles: list[str] = Field(default=["system", "user"])
    environment: ClassVar[BaseEnvironment] = Environment

    @property
    def role_regex(self) -> Pattern[str]:
        return re.compile("|".join([f"\n\n{role}:" for role in self.roles]))

    def render(self: Self, **kwargs: Any) -> str:
        return self.environment.render(self.content, **kwargs)

    def render_to_messages(
        self: Self,
        **kwargs: Any,
    ) -> list[Message]:
        pairs = split_text_by_tokens(
            text=self.render(**kwargs),
            split_tokens=[f"\n{role}" for role in self.roles],
        )
        return [
            Message(
                role=pair[0].strip(),
                content=pair[1],
            )
            for pair in pairs
        ]
