import asyncio
from functools import partial, wraps
from typing import (
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

from openai.types.images_response import ImagesResponse
from pydantic import BaseModel, Field
from typing_extensions import NotRequired, ParamSpec, Self, Unpack

from marvin.client.openai import MarvinImage
from marvin.components.prompt.fn import PromptFunction
from marvin.utilities.jinja import (
    BaseEnvironment,
)

T = TypeVar("T")

P = ParamSpec("P")


class AIImageKwargs(TypedDict):
    environment: NotRequired[BaseEnvironment]
    prompt: NotRequired[str]
    generate: NotRequired[Callable[..., "ImagesResponse"]]
    agenerate: NotRequired[Callable[..., Coroutine[Any, Any, "ImagesResponse"]]]


class AIImageKwargsDefaults(BaseModel):
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = None
    generate: Optional[Callable[..., "ImagesResponse"]] = Field(
        default_factory=lambda: MarvinImage.generate
    )
    agenerate: Optional[Callable[..., Coroutine[Any, Any, "ImagesResponse"]]] = Field(
        default_factory=lambda: MarvinImage.agenerate
    )


class AIImage(MarvinImage, Generic[P]):
    fn: Optional[Callable[P, Any]] = None
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = Field(default=None)

    def __call__(
        self, *args: P.args, **kwargs: P.kwargs
    ) -> Union["ImagesResponse", Coroutine[Any, Any, "ImagesResponse"]]:
        if asyncio.iscoroutinefunction(self.fn):
            return self.acall(*args, **kwargs)
        return self.call(*args, **kwargs)

    def call(self, *args: P.args, **kwargs: P.kwargs) -> "ImagesResponse":
        prompt_str = self.as_prompt(*args, **kwargs)
        response = self.generate(prompt=prompt_str)
        return response

    async def acall(self, *args: P.args, **kwargs: P.kwargs) -> "ImagesResponse":
        prompt_str = self.as_prompt(*args, **kwargs)
        response = await self.agenerate(prompt=prompt_str)
        return response

    def as_prompt(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> str:
        return (
            PromptFunction[BaseModel]
            .as_tool_call(
                fn=self.fn,
                environment=self.environment,
                prompt=self.prompt,
            )(*args, **kwargs)
            .messages[0]
            .content
        )

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        **kwargs: Unpack[AIImageKwargs],
    ) -> Callable[P, Self]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Callable[P, Any],
        **kwargs: Unpack[AIImageKwargs],
    ) -> Self:
        pass

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, Any]] = None,
        **kwargs: Unpack[AIImageKwargs],
    ) -> Union[Self, Callable[[Callable[P, Any]], Self]]:
        passed_kwargs: dict[str, Any] = {
            k: v for k, v in kwargs.items() if v is not None
        }
        if fn is None:
            return partial(
                cls,
                **passed_kwargs,
            )

        return cls(
            fn=fn,
            **passed_kwargs,
        )


def ai_image(
    fn: Optional[Callable[P, Any]] = None,
    **kwargs: Unpack[AIImageKwargs],
) -> Union[
    Callable[
        [Callable[P, Any]],
        Callable[P, Union["ImagesResponse", Coroutine[Any, Any, "ImagesResponse"]]],
    ],
    Callable[P, Union["ImagesResponse", Coroutine[Any, Any, "ImagesResponse"]]],
]:
    def wrapper(
        func: Callable[P, Any], *args_: P.args, **kwargs_: P.kwargs
    ) -> Union["ImagesResponse", Coroutine[Any, Any, "ImagesResponse"]]:
        return AIImage[P].as_decorator(
            func, **AIImageKwargsDefaults(**kwargs).model_dump(exclude_none=True)
        )(*args_, **kwargs_)

    if fn is not None:
        return wraps(fn)(partial(wrapper, fn))

    def decorator(
        fn: Callable[P, Any]
    ) -> Callable[P, Union["ImagesResponse", Coroutine[Any, Any, "ImagesResponse"]]]:
        return wraps(fn)(partial(wrapper, fn))

    return decorator
