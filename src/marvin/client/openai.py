from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Optional,
    TypeVar,
    Union,
    overload,
)

import pydantic
from marvin import settings
from marvin._mappings.base_model import cast_model_to_toolset
from marvin._mappings.chat_completion import chat_completion_to_model
from openai import Client
from openai.types.chat import (
    ChatCompletion,
)
from typing_extensions import Concatenate, ParamSpec

if TYPE_CHECKING:
    from openai._base_client import HttpxBinaryResponseContent
    from openai.types import ImagesResponse


P = ParamSpec("P")
T = TypeVar("T", bound=pydantic.BaseModel)


def with_response_model(
    create: Callable[P, "ChatCompletion"],
) -> Callable[Concatenate[type[T], P,], Union["ChatCompletion", T],]:
    def create_wrapper(
        response_model: type[T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        if response_model:
            toolset = cast_model_to_toolset(response_model)
            kwargs.update(**toolset.model_dump())
        response = create(*args, **kwargs)
        return chat_completion_to_model(response_model, response)

    return create_wrapper


class MarvinClient(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True,
    )
    client: Client = pydantic.Field(
        default_factory=lambda: Client(
            api_key=getattr(settings.openai.api_key, "get_secret_value", lambda: None)()
        )
    )

    @classmethod
    def wrap(cls, client: Client) -> "Client":
        client.chat.completions.create = cls(client=client).chat  # type: ignore
        return client

    @overload
    def chat(
        self,
        *,
        response_model: None = None,
        completion: Optional[Callable[..., "ChatCompletion"]] = None,
        **kwargs: Any,
    ) -> "ChatCompletion":
        pass

    @overload
    def chat(
        self,
        *,
        response_model: type[T],
        completion: Optional[Callable[..., "ChatCompletion"]] = None,
        **kwargs: Any,
    ) -> T:
        pass

    def chat(
        self,
        *,
        response_model: Optional[type[T]] = None,
        completion: Optional[Callable[..., "ChatCompletion"]] = None,
        **kwargs: Any,
    ) -> Union["ChatCompletion", T]:
        from marvin import settings

        defaults: dict[str, Any] = settings.openai.chat.completions.model_dump()
        create: Callable[..., "ChatCompletion"] = (
            completion or self.client.chat.completions.create
        )
        if not response_model:
            response: "ChatCompletion" = create(**defaults | kwargs)
            return response
        else:
            return with_response_model(create)(response_model, **defaults | kwargs)

    def paint(
        self,
        **kwargs: Any,
    ) -> "ImagesResponse":
        from marvin import settings

        return self.client.images.generate(
            **settings.openai.images.model_dump() | kwargs
        )

    def speak(
        self,
        input: str,
        file: Optional[Path] = None,
        **kwargs: Any,
    ) -> Optional["HttpxBinaryResponseContent"]:
        from marvin import settings

        response = self.client.audio.speech.create(
            input=input, **settings.openai.audio.speech.model_dump() | kwargs
        )
        if file:
            response.stream_to_file(file)
            return None
        return response


def paint(
    prompt: str,
    *,
    client: Optional[Client] = None,
    **kwargs: Any,
) -> "ImagesResponse":
    if client is None:
        return MarvinClient().paint(prompt=prompt, **kwargs)
    return MarvinClient(client=client).paint(prompt=prompt, **kwargs)


def speak(
    input: str,
    file: Path,
    client: Optional[Client] = None,
    **kwargs: Any,
) -> Optional["HttpxBinaryResponseContent"]:
    if client is None:
        return MarvinClient().speak(input=input, file=file, **kwargs)
    return MarvinClient(client=client).speak(input=input, file=file, **kwargs)


class MarvinChatCompletion(pydantic.BaseModel):
    create: Callable[..., "ChatCompletion"] = pydantic.Field(
        default_factory=lambda: MarvinClient().chat
    )
    acreate: Callable[..., Coroutine[Any, Any, "ChatCompletion"]] = pydantic.Field(
        default_factory=lambda: MarvinClient().chat
    )


class MarvinImage(pydantic.BaseModel):
    generate: Callable[..., "ImagesResponse"] = pydantic.Field(
        default_factory=lambda: MarvinClient().paint
    )
    agenerate: Callable[..., Coroutine[Any, Any, "ImagesResponse"]] = pydantic.Field(
        default_factory=lambda: MarvinClient().paint
    )
