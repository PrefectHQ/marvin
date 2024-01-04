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

from openai import AsyncClient, Client
from openai._base_client import HttpxBinaryResponseContent as AudioResponse
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import NotRequired, ParamSpec, Self, Unpack

from marvin.client.openai import AsyncMarvinClient, MarvinClient
from marvin.components.prompt.fn import PromptFunction
from marvin.prompts.speech import SPEECH_PROMPT
from marvin.utilities.jinja import (
    BaseEnvironment,
)

T = TypeVar("T")
P = ParamSpec("P")


class SpeechKwargs(TypedDict):
    environment: NotRequired[BaseEnvironment]
    prompt: NotRequired[str]
    client: NotRequired[Client]
    aclient: NotRequired[AsyncClient]


class SpeechKwargsDefaults(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = SPEECH_PROMPT
    client: Optional[Client] = None
    aclient: Optional[AsyncClient] = None


class Speech(BaseModel, Generic[P]):
    model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())
    fn: Optional[Callable[P, Any]] = None
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = Field(default=SPEECH_PROMPT)
    client: Client = Field(default_factory=lambda: MarvinClient().client)
    aclient: AsyncClient = Field(default_factory=lambda: AsyncMarvinClient().client)

    def __call__(
        self, *args: P.args, **kwargs: P.kwargs
    ) -> Union[AudioResponse, Coroutine[Any, Any, AudioResponse]]:
        if asyncio.iscoroutinefunction(self.fn):
            return self.acall(*args, **kwargs)
        return self.call(*args, **kwargs)

    def call(self, *args: P.args, **kwargs: P.kwargs) -> AudioResponse:
        prompt_str = self.as_prompt(*args, **kwargs)
        return MarvinClient(client=self.client).speak(input=prompt_str)

    async def acall(self, *args: P.args, **kwargs: P.kwargs) -> AudioResponse:
        prompt_str = self.as_prompt(*args, **kwargs)
        return await AsyncMarvinClient(client=self.aclient).speak(input=prompt_str)

    def as_prompt(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> str:
        tool_call = PromptFunction[BaseModel].as_tool_call(
            fn=self.fn,
            environment=self.environment,
            prompt=self.prompt,
        )
        return tool_call(*args, **kwargs).messages[0].content

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        **kwargs: Unpack[SpeechKwargs],
    ) -> Callable[P, Self]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Callable[P, Any],
        **kwargs: Unpack[SpeechKwargs],
    ) -> Self:
        pass

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, Any]] = None,
        **kwargs: Unpack[SpeechKwargs],
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


def speech(
    fn: Optional[Callable[P, Any]] = None,
    **kwargs: Unpack[SpeechKwargs],
) -> Union[
    Callable[
        [Callable[P, Any]],
        Callable[P, Union[AudioResponse, Coroutine[Any, Any, AudioResponse]]],
    ],
    Callable[P, Union[AudioResponse, Coroutine[Any, Any, AudioResponse]]],
]:
    def wrapper(
        func: Callable[P, Any], *args_: P.args, **kwargs_: P.kwargs
    ) -> Union[AudioResponse, Coroutine[Any, Any, AudioResponse]]:
        f = Speech[P].as_decorator(
            func, **SpeechKwargsDefaults(**kwargs).model_dump(exclude_none=True)
        )
        return f(*args_, **kwargs_)

    if fn is not None:
        return wraps(fn)(partial(wrapper, fn))

    def decorator(
        fn: Callable[P, Any],
    ) -> Callable[P, Union[AudioResponse, Coroutine[Any, Any, AudioResponse]]]:
        return wraps(fn)(partial(wrapper, fn))

    return decorator
