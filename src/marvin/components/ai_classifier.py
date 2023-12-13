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

from pydantic import BaseModel, Field
from typing_extensions import NotRequired, ParamSpec, Self, Unpack

from marvin._mappings.chat_completion import chat_completion_to_type
from marvin.client.openai import MarvinChatCompletion
from marvin.components.prompt.fn import PromptFunction
from marvin.utilities.jinja import BaseEnvironment

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion

T = TypeVar("T")

P = ParamSpec("P")


class AIClassifierKwargs(TypedDict):
    environment: NotRequired[BaseEnvironment]
    prompt: NotRequired[str]
    encoder: NotRequired[Callable[[str], list[int]]]
    create: NotRequired[Callable[..., "ChatCompletion"]]
    acreate: NotRequired[Callable[..., Coroutine[Any, Any, "ChatCompletion"]]]


class AIClassifierKwargsDefaults(BaseModel):
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = None
    encoder: Optional[Callable[[str], list[int]]] = None
    create: Optional[Callable[..., "ChatCompletion"]] = Field(
        default_factory=lambda: MarvinChatCompletion.create
    )
    acreate: Optional[Callable[..., Coroutine[Any, Any, "ChatCompletion"]]] = Field(
        default_factory=lambda: MarvinChatCompletion.acreate
    )


class AIClassifier(
    MarvinChatCompletion,
    Generic[P, T],
):
    fn: Optional[Callable[P, Union[T, Coroutine[Any, Any, T]]]] = None
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = Field(default=inspect.cleandoc("""
        ## Expert Classifier

        **Objective**: You are an expert classifier that always chooses correctly.

        ### Description
        {{ _doc }}

        ### Data
        {% for arg, value in _arguments.items() %}
        - **{{ arg }}**: {{ value }}
        {% endfor %}

        ### Response Format
        You must classify into one of the following classes:
        {% for option in _options %}
        - Class {{ loop.index0 }} (value: {{ option }})
        {% endfor %}
    """))
    encoder: Callable[[str], list[int]] = Field(default=None)
    max_tokens: int = 1
    temperature: float = 0.0

    def __call__(
        self, *args: P.args, **kwargs: P.kwargs
    ) -> Union[T, Coroutine[Any, Any, T]]:
        if asyncio.iscoroutinefunction(self.fn):
            return self.acall(*args, **kwargs)
        return self.call(*args, **kwargs)

    def call(self, *args: P.args, **kwargs: P.kwargs) -> T:
        prompt = self.as_prompt(*args, **kwargs)
        response = self.create(**prompt.serialize())
        return chat_completion_to_type(self.fn.__annotations__["return"], response)

    async def acall(self, *args: P.args, **kwargs: P.kwargs) -> T:
        prompt = self.as_prompt(*args, **kwargs)
        response = await self.acreate(**prompt.serialize())
        return chat_completion_to_type(self.fn.__annotations__["return"], response)

    def map(self, *arg_list: list[Any], **kwarg_list: list[Any]) -> list[T]:
        return [
            self.call(*args, **{k: v[i] for k, v in kwarg_list.items()})
            for i, args in enumerate(zip(*arg_list))
        ]

    async def amap(self, *arg_list: list[Any], **kwarg_list: list[Any]) -> list[T]:
        return await asyncio.gather(
            *[
                self.acall(*args, **{k: v[i] for k, v in kwarg_list.items()})
                for i, args in enumerate(zip(*arg_list))
            ]
        )

    def as_prompt(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> PromptFunction[BaseModel]:
        return PromptFunction[BaseModel].as_grammar(
            fn=self.fn,
            **self.model_dump(exclude={"create", "acreate", "fn"}, exclude_none=True),
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
        **kwargs: Unpack[AIClassifierKwargs],
    ) -> Callable[P, Self]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Callable[P, Union[T, Coroutine[Any, Any, T]]],
        **kwargs: Unpack[AIClassifierKwargs],
    ) -> Self:
        pass

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, Union[T, Coroutine[Any, Any, T]]]] = None,
        **kwargs: Unpack[AIClassifierKwargs],
    ) -> Union[Callable[[Callable[P, Union[T, Coroutine[Any, Any, T]]]], Self], Self]:
        def decorator(func: Callable[P, Union[T, Coroutine[Any, Any, T]]]) -> Self:
            return cls(
                fn=func,
                **AIClassifierKwargsDefaults(**kwargs).model_dump(exclude_none=True),
            )

        if fn is not None:
            return decorator(fn)

        return decorator


@overload
def ai_classifier(
    **kwargs: Unpack[AIClassifierKwargs],
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    pass


@overload
def ai_classifier(
    fn: Callable[P, T],
    **kwargs: Unpack[AIClassifierKwargs],
) -> Callable[P, T]:
    pass


def ai_classifier(
    fn: Optional[Callable[P, Union[T, Coroutine[Any, Any, T]]]] = None,
    **kwargs: Unpack[AIClassifierKwargs],
) -> Union[
    Callable[
        [Callable[P, Union[T, Coroutine[Any, Any, T]]]],
        Callable[P, Union[T, Coroutine[Any, Any, T]]],
    ],
    Callable[P, Union[T, Coroutine[Any, Any, T]]],
]:
    if fn is not None:
        return AIClassifier[P, T].as_decorator(
            fn=fn, **AIClassifierKwargsDefaults(**kwargs).model_dump(exclude_none=True)
        )

    def decorator(
        func: Callable[P, Union[T, Coroutine[Any, Any, T]]]
    ) -> Callable[P, Union[T, Coroutine[Any, Any, T]]]:
        return AIClassifier[P, T].as_decorator(
            fn=func,
            **AIClassifierKwargsDefaults(**kwargs).model_dump(exclude_none=True),
        )

    return decorator
