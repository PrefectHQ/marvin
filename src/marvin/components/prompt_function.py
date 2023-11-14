import inspect
import re
from functools import partial, wraps
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    ParamSpec,
    Self,
    TypeVar,
    Union,
    overload,
)

import pydantic
from pydantic import BaseModel

from marvin.requests import BaseMessage as Message
from marvin.requests import Tool
from marvin.serializers import create_tool_from_type
from marvin.utilities.jinja import (
    BaseEnvironment,
    Transcript,
)

P = ParamSpec("P")
T = TypeVar("T")
U = TypeVar("U", bound=BaseModel)


class Prompt(pydantic.BaseModel, Generic[U]):
    messages: list[Message]
    tools: Optional[list[Tool[U]]] = pydantic.Field(default=None)
    tool_choice: Optional[dict[str, Any]] = pydantic.Field(default=None)
    logit_bias: Optional[dict[int, float]] = pydantic.Field(default=None)
    max_tokens: Optional[int] = pydantic.Field(default=None)

    def serialize(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class PromptFn(Prompt[U]):
    messages: list[Message]
    tools: Optional[list[Tool[U]]] = pydantic.Field(default=None)
    tool_choice: Optional[dict[str, Any]] = pydantic.Field(default=None)
    logit_bias: Optional[dict[int, float]] = pydantic.Field(default=None)
    max_tokens: Optional[int] = pydantic.Field(default=None)

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        model_name: str = "FormatResponse",
        model_description: str = "Formats the response.",
        field_name: str = "data",
        field_description: str = "The data to format.",
    ) -> Callable[[Callable[P, Any]], Callable[P, Self]]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, Any]] = None,
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        model_name: str = "FormatResponse",
        model_description: str = "Formats the response.",
        field_name: str = "data",
        field_description: str = "The data to format.",
    ) -> Callable[P, Self]:
        pass

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, Any]] = None,
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        model_name: str = "FormatResponse",
        model_description: str = "Formats the response.",
        field_name: str = "data",
        field_description: str = "The data to format.",
        **kwargs: Any,
    ) -> Union[
        Callable[[Callable[P, Any]], Callable[P, Self]],
        Callable[P, Self],
    ]:
        def wrapper(func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs) -> Self:
            tool = create_tool_from_type(
                _type=inspect.signature(func).return_annotation,
                model_name=model_name,
                model_description=model_description,
                field_name=field_name,
                field_description=field_description,
            )

            signature = inspect.signature(func)
            params = signature.bind(*args, **kwargs)
            params.apply_defaults()
            return cls(
                messages=Transcript(
                    content=prompt or func.__doc__ or ""
                ).render_to_messages(
                    **kwargs,
                    **params.arguments,
                    _arguments=params.arguments,
                    _response_model=tool,
                    _source_code=(
                        "\ndef"
                        + "def".join(re.split("def", inspect.getsource(func))[1:])
                    ),
                ),
                tool_choice={
                    "type": "function",
                    "function": {"name": tool.function.name},
                },
                tools=[tool],
            )

        if fn is not None:
            return wraps(fn)(partial(wrapper, fn))

        def decorator(fn: Callable[P, Any]) -> Callable[P, Self]:
            return wraps(fn)(partial(wrapper, fn))

        return decorator


def prompt_fn(
    fn: Optional[Callable[P, T]] = None,
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = None,
    model_name: str = "FormatResponse",
    model_description: str = "Formats the response.",
    field_name: str = "data",
    field_description: str = "The data to format.",
    **kwargs: Any,
) -> Union[
    Callable[[Callable[P, T]], Callable[P, dict[str, Any]]],
    Callable[P, dict[str, Any]],
]:
    def wrapper(
        func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs
    ) -> dict[str, Any]:
        return PromptFn.as_decorator(
            fn=func,
            environment=environment,
            prompt=prompt,
            model_name=model_name,
            model_description=model_description,
            field_name=field_name,
            field_description=field_description,
            **kwargs,
        )(*args, **kwargs).serialize()

    if fn is not None:
        return wraps(fn)(partial(wrapper, fn))

    def decorator(fn: Callable[P, Any]) -> Callable[P, dict[str, Any]]:
        return wraps(fn)(partial(wrapper, fn))

    return decorator
