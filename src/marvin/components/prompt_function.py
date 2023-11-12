import inspect
import re
from functools import partial, wraps
from re import Pattern, compile
from typing import Any, Callable, ClassVar, Optional, ParamSpec, Self, Union, overload

import pydantic

from marvin.requests import BaseMessage as Message
from marvin.requests import ChatRequest
from marvin.serializers import create_tool_from_type
from marvin.utilities.asyncio import run_sync
from marvin.utilities.jinja import (
    BaseEnvironment,
    split_text_by_tokens,
)
from marvin.utilities.jinja import Environment as JinjaEnvironment
from marvin.utilities.openai import get_client

P = ParamSpec("P")


class Transcript(pydantic.BaseModel):
    content: str
    roles: list[str] = pydantic.Field(default=["system", "user"])
    environment: ClassVar[BaseEnvironment] = JinjaEnvironment

    @property
    def role_regex(self) -> Pattern[str]:
        return compile("|".join([f"\n\n{role}:" for role in self.roles]))

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


class Prompt(pydantic.BaseModel):
    messages: list[Message]
    tools: Optional[list[dict[str, Any]]] = pydantic.Field(default=None)
    tool_choice: Optional[dict[str, Any]] = pydantic.Field(default=None)
    logit_bias: Optional[dict[int, float]] = pydantic.Field(default=None)
    max_tokens: Optional[int] = pydantic.Field(default=None)

    def serialize(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)

    def call(self) -> Any:
        return run_sync(self.acall())

    async def acall(self) -> Any:
        payload = ChatRequest(**self.serialize()).model_dump(exclude_none=True)
        return await get_client().chat.completions.create(**payload)  # type: ignore

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, Any]] = None,
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        serialize: bool = True,
        model_name: str = "FormatResponse",
        model_description: str = "Formats the response.",
        field_name: str = "data",
        field_description: str = "The data to format.",
    ) -> Union[
        Callable[[Callable[P, Any]], Callable[P, Any]],
        Callable[[Callable[P, Any]], Callable[P, Union[dict[str, Any], Self]]],
        Callable[P, Union[dict[str, Any], Self]],
    ]:
        def wrapper(
            fn: Callable[P, Any], *args: P.args, **kwargs: P.kwargs
        ) -> Union[dict[str, Any], Self]:
            tool = create_tool_from_type(
                _type=inspect.signature(fn).return_annotation,
                name=model_name,
                description=model_description,
                field_name=field_name,
                field_description=field_description,
            )

            signature = inspect.signature(fn)
            params = signature.bind(*args, **kwargs)
            params.apply_defaults()

            promptfn = cls(
                messages=Transcript(
                    content=prompt or fn.__doc__ or ""
                ).render_to_messages(
                    **params.arguments,
                    _arguments=params.arguments,
                    _source_code=(
                        "\ndef" + "def".join(re.split("def", inspect.getsource(fn))[1:])
                    ),
                ),
                tool_choice={
                    "type": "function",
                    "function": {"name": tool.function.name},
                },
                tools=[tool.model_dump()],
            )
            if serialize:
                return promptfn.serialize()
            return promptfn

        if fn is not None:
            return wraps(fn)(partial(wrapper, fn))

        def decorator(
            fn: Callable[P, None]
        ) -> Callable[P, Union[dict[str, Any], Self]]:
            return wraps(fn)(partial(wrapper, fn))

        return decorator


prompt_fn = Prompt.as_decorator
PromptFn = Prompt


@Prompt.as_decorator()
def add(x: int, y: int = 2) -> int:
    """
    Add two numbers together.
    """
    return x + 1


add(1, 2)
