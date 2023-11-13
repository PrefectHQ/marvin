import inspect
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Pattern, Self, Union
from zoneinfo import ZoneInfo

import pydantic
from jinja2 import Environment as JinjaEnvironment
from jinja2 import StrictUndefined, select_autoescape
from jinja2 import Template as BaseTemplate

from marvin.requests import BaseMessage as Message


class BaseEnvironment(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    environment: JinjaEnvironment = pydantic.Field(
        default=JinjaEnvironment(
            autoescape=select_autoescape(default_for_string=False),
            trim_blocks=True,
            lstrip_blocks=True,
            auto_reload=True,
            undefined=StrictUndefined,
        )
    )

    globals: dict[str, Any] = pydantic.Field(
        default_factory=lambda: {
            "now": lambda: datetime.now(ZoneInfo("UTC")),
            "inspect": inspect,
        }
    )

    @pydantic.model_validator(mode="after")
    def setup_globals(self: Self) -> Self:
        self.environment.globals.update(self.globals)  # type: ignore
        return self

    def render(self, template: Union[str, BaseTemplate], **kwargs: Any) -> str:
        if isinstance(template, str):
            return self.environment.from_string(template).render(**kwargs)
        return template.render(**kwargs)


Environment = BaseEnvironment()


def split_text_by_tokens(
    text: str,
    split_tokens: list[str],
    environment: JinjaEnvironment = Environment.environment,
) -> list[tuple[str, str]]:
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


class Transcript(pydantic.BaseModel):
    content: str
    roles: list[str] = pydantic.Field(default=["system", "user"])
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
