from functools import partial
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Optional,
    TypeVar,
    Union,
)

import pydantic
from openai import AsyncClient, Client, NotFoundError
from openai.types.chat import (
    ChatCompletion,
)
from typing_extensions import ParamSpec

import marvin
from marvin import settings
from marvin.types import ChatRequest, ImageRequest, VisionRequest
from marvin.utilities.logging import get_logger

if TYPE_CHECKING:
    from openai._base_client import HttpxBinaryResponseContent
    from openai.types import ImagesResponse


P = ParamSpec("P")
T = TypeVar("T", bound=pydantic.BaseModel)


def _get_default_client(client_type: str) -> Union[Client, AsyncClient]:
    if getattr(settings, "use_azure_openai", False):
        from openai import AsyncAzureOpenAI, AzureOpenAI

        client_class = AsyncAzureOpenAI if client_type == "async" else AzureOpenAI

        try:
            return client_class(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
            )
        except AttributeError:
            raise ValueError(
                "To use Azure OpenAI, please set all of the following environment variables in `~/.marvin/.env`:"
                "\n\n"
                "```"
                "\nMARVIN_USE_AZURE_OPENAI=true"
                "\nMARVIN_AZURE_OPENAI_API_KEY=..."
                "\nMARVIN_AZURE_OPENAI_API_VERSION=..."
                "\nMARVIN_AZURE_OPENAI_ENDPOINT=..."
                "\nMARVIN_AZURE_OPENAI_DEPLOYMENT_NAME=..."
                "\n```"
            )

    api_key = (
        settings.openai.api_key.get_secret_value() if settings.openai.api_key else None
    )
    if not api_key:
        raise ValueError(
            "OpenAI API key not found. Please either set `MARVIN_OPENAI_API_KEY` in"
            " `~/.marvin/.env` or otherwise set `OPENAI_API_KEY` in your environment."
        )
    if client_type not in ["sync", "async"]:
        raise ValueError(f"Invalid client type {client_type!r}")

    client_class = Client if client_type == "sync" else AsyncClient
    return client_class(api_key=api_key, organization=settings.openai.organization)


class MarvinClient(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True, protected_namespaces=()
    )

    client: Client = pydantic.Field(default_factory=lambda: _get_default_client("sync"))

    @classmethod
    def wrap(cls, client: Client) -> "Client":
        client.chat.completions.create = partial(
            cls(client=client).generate_chat, completion=client.chat.completions.create
        )  # type: ignore #noqa
        return client

    def generate_chat(
        self,
        *,
        completion: Optional[Callable[..., "ChatCompletion"]] = None,
        **kwargs: Any,
    ) -> Union["ChatCompletion", T]:
        create: Callable[..., "ChatCompletion"] = (
            completion or self.client.chat.completions.create
        )
        # validate request
        request = ChatRequest(**kwargs)
        try:
            response: "ChatCompletion" = create(**request.model_dump(exclude_none=True))
        except NotFoundError as e:
            if "you do not have access" in str(e):
                get_logger().warning(
                    f"Marvin's default chat model is {marvin.settings.openai.chat.completions.model!r}, which"
                    " your API key likely does not give you access to. This API call will fall back to the"
                    f" {marvin.settings.openai.chat.completions._fallback_model!r} model. To avoid this warning,"
                    " please set `MARVIN_OPENAI_CHAT_COMPLETIONS_MODEL=<accessible model>` in `~/.marvin/.env` -"
                    f" for example, `gpt-3.5-turbo`.\n\n {e}"
                )
                return create(
                    **request.model_dump(
                        exclude_none=True,
                    )
                    | dict(
                        model=marvin.settings.openai.chat.completions._fallback_model
                    )
                )
            else:
                raise e
        return response

    def generate_vision(
        self,
        *,
        completion: Optional[Callable[..., "ChatCompletion"]] = None,
        **kwargs: Any,
    ) -> Union["ChatCompletion", T]:
        create: Callable[..., "ChatCompletion"] = (
            completion or self.client.chat.completions.create
        )
        # validate request
        request = VisionRequest(**kwargs)
        response: "ChatCompletion" = create(**request.model_dump(exclude_none=True))
        return response

    def generate_image(
        self,
        **kwargs: Any,
    ) -> "ImagesResponse":
        # validate request
        request = ImageRequest(**marvin.settings.openai.images.model_dump() | kwargs)
        return self.client.images.generate(**request.model_dump(exclude_none=True))

    def generate_speech(
        self,
        input: str,
        file: Optional[Path] = None,
        **kwargs: Any,
    ) -> Optional["HttpxBinaryResponseContent"]:
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
            cls(client=client).generate_chat, completion=client.chat.completions.create
        )  # type: ignore #noqa
        return client

    async def generate_chat(
        self,
        **kwargs: Any,
    ) -> Union["ChatCompletion", T]:
        create = self.client.chat.completions.create
        # validate request
        request = ChatRequest(**kwargs)
        try:
            response: "ChatCompletion" = await create(
                **request.model_dump(exclude_none=True)
            )
        except NotFoundError as e:
            if "you do not have access" in str(e):
                get_logger().warning(
                    f"Marvin's default chat model is {marvin.settings.openai.chat.completions.model!r}, which"
                    " your API key likely does not give you access to. This API call will fall back to the"
                    f" {marvin.settings.openai.chat.completions._fallback_model!r} model. To avoid this warning,"
                    " please set `MARVIN_OPENAI_CHAT_COMPLETIONS_MODEL=<accessible model>` in `~/.marvin/.env` -"
                    f" for example, `gpt-3.5-turbo`.\n\n {e}"
                )
                return await create(
                    **request.model_dump(
                        exclude_none=True,
                    )
                    | dict(
                        model=marvin.settings.openai.chat.completions._fallback_model
                    )
                )
            else:
                raise e
        return response

    async def generate_vision(
        self,
        *,
        completion: Optional[Callable[..., "ChatCompletion"]] = None,
        **kwargs: Any,
    ) -> Union["ChatCompletion", T]:
        create: Callable[..., "ChatCompletion"] = (
            completion or self.client.chat.completions.create
        )
        # validate request
        request = VisionRequest(**kwargs)
        response: "ChatCompletion" = await create(
            **request.model_dump(exclude_none=True)
        )
        return response

    async def generate_image(
        self,
        **kwargs: Any,
    ) -> "ImagesResponse":
        # validate request
        request = ImageRequest(**marvin.settings.openai.images.model_dump() | kwargs)
        return await self.client.images.generate(
            **request.model_dump(exclude_none=True)
        )

    async def generate_audio(
        self,
        input: str,
        file: Optional[Path] = None,
        **kwargs: Any,
    ) -> Optional["HttpxBinaryResponseContent"]:
        response = await self.client.audio.speech.create(
            input=input, **settings.openai.audio.speech.model_dump() | kwargs
        )
        if file:
            response.stream_to_file(file)
            return None
        return response
