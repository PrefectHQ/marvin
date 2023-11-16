import asyncio
import inspect
import json
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    TypeVar,
    Union,
    overload,
)

from pydantic import BaseModel, Field, ValidationError
from typing_extensions import ParamSpec, Self

from marvin.components.prompt import PromptFunction
from marvin.serializers import create_tool_from_type
from marvin.utilities.asyncio import (
    ExposeSyncMethodsMixin,
    expose_sync_method,
    run_async,
)
from marvin.utilities.jinja import (
    BaseEnvironment,
)

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion

T = TypeVar("T")

P = ParamSpec("P")


class AIFunction(BaseModel, Generic[P, T], ExposeSyncMethodsMixin):
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

    create: Optional[Callable[..., "ChatCompletion"]] = Field(default=None)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Union[T, Awaitable[T]]:
        if self.fn is None:
            raise NotImplementedError

        from marvin import settings

        is_async_fn = asyncio.iscoroutinefunction(self.fn)

        call = "async_call" if is_async_fn else "sync_call"
        create = (
            self.create or settings.openai.chat.completions.acreate
            if is_async_fn
            else settings.openai.chat.completions.create
        )

        return getattr(self, call)(create, *args, **kwargs)

    async def async_call(self, acreate, *args: P.args, **kwargs: P.kwargs) -> T:
        _response = await acreate(**self.as_prompt(*args, **kwargs).serialize())
        return self.parse(_response)

    def sync_call(self, create, *args: P.args, **kwargs: P.kwargs) -> T:
        _response = create(**self.as_prompt(*args, **kwargs).serialize())
        return self.parse(_response)

    def parse(self, response: "ChatCompletion") -> T:
        tool_calls = response.choices[0].message.tool_calls
        if tool_calls is None:
            raise NotImplementedError
        if self.fn is None:
            raise NotImplementedError
        arguments = tool_calls[0].function.arguments

        tool = create_tool_from_type(
            _type=self.fn.__annotations__["return"],
            model_name=self.name,
            model_description=self.description,
            field_name=self.field_name,
            field_description=self.field_description,
        ).function
        if not tool or not tool.model:
            raise NotImplementedError
        try:
            return getattr(tool.model.model_validate_json(arguments), self.field_name)
        except ValidationError:
            # When the user provides a dict obj as a type hint, the arguments
            # are returned usually as an object and not a nested dict.
            _arguments: str = json.dumps({self.field_name: json.loads(arguments)})
            return getattr(tool.model.model_validate_json(_arguments), self.field_name)

    @expose_sync_method("map")
    async def amap(self, *map_args: list[Any], **map_kwargs: list[Any]) -> list[T]:
        """
        Map the AI function over a sequence of arguments. Runs concurrently.

        Arguments should be provided as if calling the function normally, but
        each argument must be a list. The function is called once for each item
        in the list, and the results are returned in a list.

        This method should be called synchronously.

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
        **render_kwargs: Any,
    ) -> Callable[..., Self]:
        def decorator(func: Callable[P, T]) -> Self:
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
    **render_kwargs: Any,
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
    **render_kwargs: Any,
) -> Callable[P, T]:
    pass


def ai_fn(
    fn: Optional[Callable[P, T]] = None,
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = None,
    model_name: str = "FormatResponse",
    model_description: str = "Formats the response.",
    field_name: str = "data",
    field_description: str = "The data to format.",
    **render_kwargs: Any,
) -> Union[Callable[[Callable[P, T]], AIFunction[P, T]], AIFunction[P, T]]:
    if fn is not None:
        return AIFunction.as_decorator(
            fn=fn,
            environment=environment,
            prompt=prompt,
            model_name=model_name,
            model_description=model_description,
            field_name=field_name,
            field_description=field_description,
            **render_kwargs,
        )

    def decorator(func: Callable[P, T]) -> AIFunction[P, T]:
        return AIFunction.as_decorator(
            fn=func,
            environment=environment,
            prompt=prompt,
            model_name=model_name,
            model_description=model_description,
            field_name=field_name,
            field_description=field_description,
            **render_kwargs,
        )

    return decorator
