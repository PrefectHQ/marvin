import asyncio
import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Generic,
    Optional,
    TypedDict,
    TypeVar,
    Union,
    overload,
)

from openai import AsyncClient, Client
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import NotRequired, ParamSpec, Self, Unpack

import marvin
from marvin._mappings.chat_completion import chat_completion_to_model
from marvin.client.openai import AsyncMarvinClient, MarvinClient
from marvin.components.prompt.fn import PromptFunction
from marvin.utilities.asyncio import (
    ExposeSyncMethodsMixin,
    expose_sync_method,
    run_async,
)
from marvin.utilities.jinja import BaseEnvironment
from marvin.utilities.logging import get_logger

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion

T = TypeVar("T")

P = ParamSpec("P")


class AIFunctionKwargs(TypedDict):
    environment: NotRequired[BaseEnvironment]
    prompt: NotRequired[str]
    model_name: NotRequired[str]
    model_description: NotRequired[str]
    field_name: NotRequired[str]
    field_description: NotRequired[str]
    client: NotRequired[Client]
    aclient: NotRequired[AsyncClient]
    model: NotRequired[str]
    temperature: NotRequired[float]


class AIFunctionKwargsDefaults(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = None
    model_name: str = "FormatResponse"
    model_description: str = "Formats the response."
    field_name: str = "data"
    field_description: str = "The data to format."
    model: str = marvin.settings.openai.chat.completions.model
    client: Optional[Client] = None
    aclient: Optional[AsyncClient] = None
    temperature: Optional[float] = marvin.settings.openai.chat.completions.temperature


class AIFunction(BaseModel, Generic[P, T], ExposeSyncMethodsMixin):
    model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())
    fn: Optional[Callable[P, T]] = None
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = Field(
        default=inspect.cleandoc(
            """
        Your job is to generate likely outputs for a Python function with the
        following signature and docstring:

        {{_source_code}}

        The user will provide function inputs (if any) and you must respond with
        the most likely result.

        \n\nHUMAN: The function was called with the following inputs:
        {%for (arg, value) in _arguments.items()%}
        - {{ arg }}: {{ value }}
        {% endfor %}



        What is its output?
    """
        )
    )
    name: str = "FormatResponse"
    description: str = "Formats the response."
    field_name: str = "data"
    field_description: str = "The data to format."
    model: Optional[str] = None
    temperature: Optional[float] = None
    client: Client = Field(default_factory=lambda: MarvinClient().client)
    aclient: AsyncClient = Field(default_factory=lambda: AsyncMarvinClient().client)

    @property
    def logger(self):
        return get_logger(self.__class__.__name__)

    def __call__(
        self, *args: P.args, **kwargs: P.kwargs
    ) -> Union[T, Coroutine[Any, Any, T]]:
        if asyncio.iscoroutinefunction(self.fn):
            return self.acall(*args, **kwargs)
        return self.call(*args, **kwargs)

    def call(self, *args: P.args, **kwargs: P.kwargs) -> T:
        prompt, model = self.as_prompt(*args, **kwargs).model_pair()
        response: ChatCompletion = MarvinClient(client=self.client).chat(
            **prompt.serialize()
        )
        self.logger.debug_kv("Calling", f"{self.fn.__name__}({args}, {kwargs})", "blue")
        return getattr(
            chat_completion_to_model(model, response, field_name=self.field_name),
            self.field_name,
        )

    async def acall(self, *args: P.args, **kwargs: P.kwargs) -> T:
        prompt, model = self.as_prompt(*args, **kwargs).model_pair()
        response: ChatCompletion = await AsyncMarvinClient(client=self.aclient).chat(
            **prompt.serialize()
        )
        return getattr(
            chat_completion_to_model(model, response, field_name=self.field_name),
            self.field_name,
        )

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
        return PromptFunction[BaseModel].as_tool_call(
            fn=self.fn,
            **self.model_dump(
                exclude={"fn", "client", "aclient", "name", "description"},
                exclude_none=True,
            ),
        )(*args, **kwargs)

    def dict(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> dict[str, Any]:
        return self.as_prompt(*args, **kwargs).serialize()

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        **kwargs: Unpack[AIFunctionKwargs],
    ) -> Callable[P, Self]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Callable[P, Union[T, Coroutine[Any, Any, T]]],
        **kwargs: Unpack[AIFunctionKwargs],
    ) -> Self:
        pass

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, Union[T, Coroutine[Any, Any, T]]]] = None,
        **kwargs: Unpack[AIFunctionKwargs],
    ) -> Union[Callable[[Callable[P, Union[T, Coroutine[Any, Any, T]]]], Self], Self]:
        def decorator(func: Callable[P, Union[T, Coroutine[Any, Any, T]]]) -> Self:
            return cls(
                fn=func,
                **AIFunctionKwargsDefaults(**kwargs).model_dump(exclude_none=True),
            )

        if fn is not None:
            return decorator(fn)

        return decorator


@overload
def ai_fn(
    **kwargs: Unpack[AIFunctionKwargs],
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    pass


@overload
def ai_fn(
    fn: Callable[P, T],
    **kwargs: Unpack[AIFunctionKwargs],
) -> Callable[P, T]:
    pass


def ai_fn(
    fn: Optional[Callable[P, Union[T, Coroutine[Any, Any, T]]]] = None,
    **kwargs: Unpack[AIFunctionKwargs],
) -> Union[
    Callable[
        [Callable[P, Union[T, Coroutine[Any, Any, T]]]],
        Callable[P, Union[T, Coroutine[Any, Any, T]]],
    ],
    Callable[P, Union[T, Coroutine[Any, Any, T]]],
]:
    if fn is not None:
        return AIFunction[P, T].as_decorator(
            fn=fn, **AIFunctionKwargsDefaults(**kwargs).model_dump(exclude_none=True)
        )

    def decorator(
        func: Callable[P, Union[T, Coroutine[Any, Any, T]]],
    ) -> Callable[P, Union[T, Coroutine[Any, Any, T]]]:
        return AIFunction[P, T].as_decorator(
            fn=func,
            **AIFunctionKwargsDefaults(**kwargs).model_dump(exclude_none=True),
        )

    return decorator
