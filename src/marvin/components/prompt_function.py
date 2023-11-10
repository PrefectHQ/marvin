import inspect
import re
from functools import partial, wraps
from re import Pattern, compile
from typing import Any, Callable, ClassVar, Optional, ParamSpec, Self, Union

import pydantic
from marvin import settings
from marvin.requests import BaseMessage as Message
from marvin.utilities.jinja import (
    BaseEnvironment,
    split_text_by_tokens,
)
from marvin.utilities.asyncio import run_sync
from marvin.utilities.jinja import Environment as JinjaEnvironment
from marvin.utilities.openai import get_client
from marvin.requests import ChatRequest
from pydantic import RootModel, create_model

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
            text=self.render(**kwargs), split_tokens=[role for role in self.roles]
        )
        return [
            Message(
                role=pair[0],
                content=pair[1],
            )
            for pair in pairs
        ]


class PromptFn(pydantic.BaseModel):
    messages: list[Message]
    tools: Optional[list[dict[str, Any]]] = pydantic.Field(default=None)
    tool_choice: Optional[dict[str, Any]] = pydantic.Field(default=None)
    logit_bias: Optional[dict[int, float]] = pydantic.Field(default={19: 1})
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
        serialize_on_call: bool = True,
        response_model_name: str = "FormatResponse",
        response_model_description: str = "Formats the response.",
        response_model_field_name: str = "data",
        model: Optional[str] = settings.openai.chat.completions.model,
    ) -> Union[
        Callable[[Callable[P, None]], Callable[P, None]],
        Callable[[Callable[P, None]], Callable[P, Union[dict[str, Any], Self]]],
        Callable[P, Union[dict[str, Any], Self]],
    ]:
        def wrapper(
            fn: Callable[P, Any], *args: P.args, **kwargs: P.kwargs
        ) -> Union[dict[str, Any], Self]:
            signature = inspect.signature(fn)
            params = signature.bind(*args, **kwargs)
            params.apply_defaults()

            response_model_fields = {
                response_model_field_name: (
                    inspect.signature(fn).return_annotation,
                    ...,
                )
            }

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
                    "function": {"name": response_model_name},
                },
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": response_model_name,
                            "description": response_model_description,
                            "parameters": {
                                **create_model(
                                    response_model_name, **response_model_fields  # type: ignore
                                ).model_json_schema()
                            },
                        },
                    }
                ],
            )
            if serialize_on_call:
                return promptfn.serialize()
            return promptfn

        if fn is not None:
            return wraps(fn)(partial(wrapper, fn))

        def decorator(
            fn: Callable[P, None]
        ) -> Callable[P, Union[dict[str, Any], Self]]:
            return wraps(fn)(partial(wrapper, fn))

        return decorator
