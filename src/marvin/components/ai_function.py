import asyncio
import inspect
import json
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    TypeVar,
    Union,
    overload,
)

from openai.types.chat import ChatCompletion
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing_extensions import ParamSpec, Self

from marvin.client.openai import MarvinAsyncClient, MarvinClient
from marvin.components.prompt import PromptFunction
from marvin.utilities.asyncio import (
    ExposeSyncMethodsMixin,
    expose_sync_method,
    run_async,
)
from marvin.utilities.jinja import (
    BaseEnvironment,
)
from marvin.utilities.logging import get_logger

T = TypeVar("T")

P = ParamSpec("P")


class AIFunction(BaseModel, Generic[P, T], ExposeSyncMethodsMixin):
    fn: Optional[Callable[P, Union[T, Awaitable[T]]]] = None
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = Field(default=inspect.cleandoc("""
        Your job is to generate likely outputs for a Python function with the
        following signature and docstring:

        {{_source_code}}

        The user will provide function inputs (if any) and you must respond with
        the most likely result.

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
    create: Callable[..., "ChatCompletion"] = Field(
        default_factory=lambda: MarvinClient().chat
    )
    acreate: Callable[..., Awaitable["ChatCompletion"]] = Field(
        default_factory=lambda: MarvinAsyncClient().chat
    )

    @field_validator("create", mode="before")
    def validate_create(cls, v: Any) -> Any:
        if not v:
            v = MarvinClient().chat
        return v

    @field_validator("acreate", mode="before")
    def validate_acreate(cls, v: Any) -> Any:
        if not v:
            v = MarvinAsyncClient().chat
        return v

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Union[T, Awaitable[T]]:
        if self.fn is None:
            raise NotImplementedError
        logger = get_logger("marvin.ai_fn")
        logger.debug_kv("AI Function Call", f"Calling {self.fn.__name__} with {args} and {kwargs}", "blue")  # type: ignore # noqa: E501
        if asyncio.iscoroutinefunction(self.fn):
            result = self.acall(self.acreate, *args, **kwargs)
        else:
            result = self.call(self.create, *args, **kwargs)
        logger.debug_kv("AI Function Call", f"Returned {result}", "blue")  # type: ignore # noqa: E501
        return result

    async def acall(
        self, acreate: Callable[..., Awaitable[Any]], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        prompt = self.as_prompt(*args, **kwargs)
        if (
            not prompt.tools
            or not prompt.tools[0].function
            or not prompt.tools[0].function.model
        ):
            raise AttributeError("Prompt must have at least one tool.")
        _model = prompt.tools[0].function.model
        _response = await acreate(**self.as_prompt(*args, **kwargs).serialize())
        return self.parse(_response, model=_model)

    def call(self, create: Callable[..., Any], *args: P.args, **kwargs: P.kwargs) -> T:
        prompt = self.as_prompt(*args, **kwargs)
        if (
            not prompt.tools
            or not prompt.tools[0].function
            or not prompt.tools[0].function.model
        ):
            raise AttributeError("Prompt must have at least one tool.")
        _model = prompt.tools[0].function.model
        _response = create(**prompt.serialize())
        return self.parse(_response, model=_model)

    def parse(self, response: "ChatCompletion", model: type[BaseModel]) -> T:
        tool_calls = response.choices[0].message.tool_calls
        if tool_calls is None:
            raise NotImplementedError
        if self.fn is None:
            raise NotImplementedError
        arguments = tool_calls[0].function.arguments
        try:
            return getattr(model.model_validate_json(arguments), self.field_name)
        except ValidationError:
            # When the user provides a dict obj as a type hint, the arguments
            # are returned usually as an object and not a nested dict.
            _arguments: str = json.dumps({self.field_name: json.loads(arguments)})
            return getattr(model.model_validate_json(_arguments), self.field_name)

    @expose_sync_method("map")
    async def amap(self, *map_args: list[Any], **map_kwargs: list[Any]) -> list[T]:
        """
        Map the AI function over a sequence of arguments. Runs concurrently.

        A `map` twin method is provided by the `expose_sync_method` decorator.

        You can use `map` or `amap` synchronously or asynchronously, respectively,
        regardless of whether the user function is synchronous or asynchronous.

        Arguments should be provided as if calling the function normally, but
        each argument must be a list. The function is called once for each item
        in the list, and the results are returned in a list.

        For example, fn.map([1, 2]) is equivalent to [fn(1), fn(2)].

        fn.map([1, 2], x=['a', 'b']) is equivalent to [fn(1, x='a'), fn(2, x='b')].
        """
        tasks: list[Any] = []
        if map_args and map_kwargs:
            max_length = max(
                len(arg) for arg in (map_args + tuple(map_kwargs.values()))
            )
        elif map_args:
            max_length = max(len(arg) for arg in map_args)
        else:
            max_length = max(len(v) for v in map_kwargs.values())

        for i in range(max_length):
            call_args = [arg[i] if i < len(arg) else None for arg in map_args]
            call_kwargs = (
                {k: v[i] if i < len(v) else None for k, v in map_kwargs.items()}
                if map_kwargs
                else {}
            )

            tasks.append(run_async(self, *call_args, **call_kwargs))

        return await asyncio.gather(*tasks)

    def as_prompt(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> PromptFunction[BaseModel]:
        return PromptFunction[BaseModel].as_function_call(
            fn=self.fn,
            environment=self.environment,
            prompt=self.prompt,
            model_name=self.name,
            model_description=self.description,
            field_name=self.field_name,
            field_description=self.field_description,
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
        create: Optional[Callable[..., ChatCompletion]] = None,
        acreate: Optional[Callable[..., Awaitable[Any]]] = None,
    ) -> Callable[P, Self]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Callable[P, Union[T, Awaitable[T]]],
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        model_name: str = "FormatResponse",
        model_description: str = "Formats the response.",
        field_name: str = "data",
        field_description: str = "The data to format.",
        create: Optional[Callable[..., ChatCompletion]] = None,
        acreate: Optional[Callable[..., Awaitable[Any]]] = None,
    ) -> Self:
        pass

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, Union[T, Awaitable[T]]]] = None,
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        model_name: str = "FormatResponse",
        model_description: str = "Formats the response.",
        field_name: str = "data",
        field_description: str = "The data to format.",
        **render_kwargs: Any,
    ) -> Union[Callable[[Callable[P, Union[T, Awaitable[T]]]], Self], Self]:
        def decorator(func: Callable[P, Union[T, Awaitable[T]]]) -> Self:
            return cls(
                fn=func,
                environment=environment,
                name=model_name,
                description=model_description,
                field_name=field_name,
                field_description=field_description,
                **({"prompt": prompt} if prompt else {}),
                **render_kwargs,
            )

        if fn is not None:
            return decorator(fn)

        return decorator


@overload
def ai_fn(
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = None,
    model_name: str = "FormatResponse",
    model_description: str = "Formats the response.",
    field_name: str = "data",
    field_description: str = "The data to format.",
    create: Optional[Callable[..., ChatCompletion]] = None,
    acreate: Optional[Callable[..., Awaitable[ChatCompletion]]] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    pass


@overload
def ai_fn(
    fn: Callable[P, T],
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = None,
    model_name: str = "FormatResponse",
    model_description: str = "Formats the response.",
    field_name: str = "data",
    field_description: str = "The data to format.",
    create: Optional[Callable[..., ChatCompletion]] = None,
    acreate: Optional[Callable[..., Awaitable[ChatCompletion]]] = None,
) -> Callable[P, T]:
    pass


def ai_fn(
    fn: Optional[Callable[P, Union[T, Awaitable[T]]]] = None,
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = None,
    model_name: str = "FormatResponse",
    model_description: str = "Formats the response.",
    field_name: str = "data",
    field_description: str = "The data to format.",
    create: Optional[Callable[..., ChatCompletion]] = None,
    acreate: Optional[Callable[..., Awaitable[ChatCompletion]]] = None,
) -> Union[
    Callable[
        [Callable[P, Union[T, Awaitable[T]]]], Callable[P, Union[T, Awaitable[T]]]
    ],
    Callable[P, Union[T, Awaitable[T]]],
]:
    if fn is not None:
        return AIFunction[P, T].as_decorator(
            fn=fn,
            environment=environment,
            prompt=prompt,
            model_name=model_name,
            model_description=model_description,
            field_name=field_name,
            field_description=field_description,
            create=create,
            acreate=acreate,
        )

    def decorator(
        func: Callable[P, Union[T, Awaitable[T]]]
    ) -> Callable[P, Union[T, Awaitable[T]]]:
        return AIFunction[P, T].as_decorator(
            fn=func,
            environment=environment,
            prompt=prompt,
            model_name=model_name,
            model_description=model_description,
            field_name=field_name,
            field_description=field_description,
            create=create,
            acreate=acreate,
        )

    return decorator
