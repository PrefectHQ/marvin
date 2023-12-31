from functools import partial
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
from openai import AsyncClient, Client
from openai.types.chat import (
    ChatCompletion,
)
from typing_extensions import Concatenate, ParamSpec

from marvin import settings
from marvin._mappings.base_model import cast_model_to_toolset
from marvin._mappings.chat_completion import chat_completion_to_model

if TYPE_CHECKING:
    from openai._base_client import HttpxBinaryResponseContent
    from openai.types import ImagesResponse


P = ParamSpec("P")
T = TypeVar("T", bound=pydantic.BaseModel)


def _get_default_client(client_type: str) -> Union[Client, AsyncClient]:
    api_key = (
        settings.openai.api_key.get_secret_value() if settings.openai.api_key else None
    )

    if not api_key:
        raise ValueError(
            "OpenAI API key not set - please set `MARVIN_OPENAI_API_KEY` in `~/.marvin/.env`."
        )

    if client_type == "sync":
        return Client(
            **settings.openai.model_dump(
                exclude={"chat", "images", "audio", "assistants", "api_key"}
            )
            | dict(api_key=api_key)
        )
    elif client_type == "async":
        return AsyncClient(
            **settings.openai.model_dump(
                exclude={"chat", "images", "audio", "assistants", "api_key"}
            )
            | dict(api_key=api_key)
        )
    else:
        raise ValueError(f"Invalid client type {client_type!r}")


def with_response_model(
    create: Callable[P, "ChatCompletion"],
) -> Callable[
    Concatenate[
        type[T],
        P,
    ],
    Union["ChatCompletion", T],
]:
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


def async_with_response_model(
    create: Callable[P, Coroutine[Any, Any, "ChatCompletion"]],
) -> Callable[
    Concatenate[
        type[T],
        P,
    ],
    Coroutine[Any, Any, Union["ChatCompletion", T]],
]:
    async def create_wrapper(
        response_model: type[T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        if response_model:
            toolset = cast_model_to_toolset(response_model)
            kwargs.update(**toolset.model_dump())
        response = await create(*args, **kwargs)
        return chat_completion_to_model(response_model, response)

    return create_wrapper


class MarvinClient(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True, protected_namespaces=()
    )

    client: Client = pydantic.Field(default_factory=lambda: _get_default_client("sync"))

    @classmethod
    def wrap(cls, client: Client) -> "Client":
        client.chat.completions.create = partial(
            cls(client=client).chat, completion=client.chat.completions.create
        )  # type: ignore #noqa
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


class AsyncMarvinClient(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True, protected_namespaces=()
    )

    client: AsyncClient = pydantic.Field(
        default_factory=lambda: _get_default_client("async")
    )

    @classmethod
    def wrap(cls, client: AsyncClient) -> "AsyncClient":
        client.chat.completions.create = partial(
            cls(client=client).chat, completion=client.chat.completions.create
        )  # type: ignore #noqa
        return client

    @overload
    async def chat(
        self,
        *,
        response_model: None = None,
        **kwargs: Any,
    ) -> "ChatCompletion":
        pass

    @overload
    async def chat(
        self,
        *,
        response_model: type[T],
        **kwargs: Any,
    ) -> T:
        pass

    async def chat(
        self,
        *,
        response_model: Optional[type[T]] = None,
        **kwargs: Any,
    ) -> Union["ChatCompletion", T]:
        from marvin import settings

        defaults: dict[str, Any] = settings.openai.chat.completions.model_dump()
        create = self.client.chat.completions.create
        if not response_model:
            response: "ChatCompletion" = await create(**defaults | kwargs)
            return response
        else:
            return await async_with_response_model(create)(
                response_model, **defaults | kwargs
            )

    async def paint(
        self,
        **kwargs: Any,
    ) -> "ImagesResponse":
        from marvin import settings

        return await self.client.images.generate(
            **settings.openai.images.model_dump() | kwargs
        )

    async def speak(
        self,
        input: str,
        file: Optional[Path] = None,
        **kwargs: Any,
    ) -> Optional["HttpxBinaryResponseContent"]:
        from marvin import settings

        response = await self.client.audio.speech.create(
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
