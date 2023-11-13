import inspect
from functools import partial
from typing import Any, Awaitable, Callable, Generic, Optional, TypeVar, Union, overload

from pydantic import BaseModel, Field
from typing_extensions import ParamSpec, Self

from marvin.components.prompt_function import Prompt
from marvin.utilities.jinja import (
    BaseEnvironment,
)

T = TypeVar("T")

P = ParamSpec("P")


class AIFunction(BaseModel, Generic[P, T]):
    fn: Optional[Callable[P, T]] = None
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = Field(default=inspect.cleandoc("""
        Your job is to generate likely outputs for a Python function with the
        following signature and docstring:

        {{_source_code}}

        The user will provide function inputs (if any) and you must respond with
        the most likely result, which must be valid, double-quoted JSON.

        user: The function was called with the following inputs:
        {%for (arg, value) in _arguments.items()%}
        - {{ arg }}: {{ value }}
        {% endfor %}

        What is its output?
    """))
    name: str = "FormatResponse"
    description: str = "Formats the response."
    field_name: str = "data"
    field_description: str = "The data to format."
    render_kwargs: dict[str, Any] = Field(default_factory=dict)

    acreate: Optional[Callable[..., Awaitable[Any]]] = Field(default=None)

    def as_prompt(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Prompt[BaseModel]:
        return Prompt[BaseModel].as_decorator(
            fn=self.fn,
            environment=self.environment,
            prompt=self.prompt,
            model_name=self.name,
            model_description=self.description,
            field_name=self.field_name,
            field_description=self.field_description,
            **self.render_kwargs,
        )(*args, **kwargs)

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
        acreate: Optional[Callable[..., Awaitable[Any]]] = None,
        **render_kwargs: Any,
    ) -> Callable[P, Self]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Callable[P, T],
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        model_name: str = "FormatResponse",
        model_description: str = "Formats the response.",
        field_name: str = "data",
        field_description: str = "The data to format.",
        acreate: Optional[Callable[..., Awaitable[Any]]] = None,
        **render_kwargs: Any,
    ) -> Self:
        pass

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, T]] = None,
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        model_name: str = "FormatResponse",
        model_description: str = "Formats the response.",
        field_name: str = "data",
        field_description: str = "The data to format.",
        acreate: Optional[Callable[..., Awaitable[Any]]] = None,
        **render_kwargs: Any,
    ) -> Union[Self, Callable[[Callable[P, T]], Self]]:
        if fn is None:
            return partial(
                cls,
                environment=environment,
                prompt=prompt,
                model_name=model_name,
                model_description=model_description,
                field_name=field_name,
                field_description=field_description,
                acreate=acreate,
                **({"prompt": prompt} if prompt else {}),
                **render_kwargs,
            )

        return cls(
            fn=fn,
            environment=environment,
            name=model_name,
            description=model_description,
            field_name=field_name,
            field_description=field_description,
            **({"prompt": prompt} if prompt else {}),
            **render_kwargs,
        )


ai_fn = AIFunction.as_decorator
