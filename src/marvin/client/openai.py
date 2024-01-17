import inspect
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

import openai
import openai.types.chat.chat_completion
import openai.types.chat.chat_completion_chunk
import pydantic
from openai import AsyncClient, Client, NotFoundError
from openai.types.chat import ChatCompletion
from pydantic import BaseModel
from typing_extensions import ParamSpec

import marvin
from marvin import settings
from marvin.types import (
    BaseMessage as Message,
)
from marvin.types import (
    ChatRequest,
    HttpxBinaryResponseContent,
    ImageRequest,
    StreamingChatResponse,
    VisionRequest,
)
from marvin.utilities.logging import get_logger

if TYPE_CHECKING:
    from openai.types import ImagesResponse


P = ParamSpec("P")
T = TypeVar("T", bound=pydantic.BaseModel)

FALLBACK_CHAT_COMPLETIONS_MODEL = "gpt-3.5-turbo"


def process_streaming_chat_response(
    completion: Optional[ChatCompletion], chunk: openai.types.chat.ChatCompletionChunk
) -> StreamingChatResponse:
    # if no completion is provided, create the initial completion from the chunk
    if completion is None:
        completion = ChatCompletion(
            id=chunk.id,
            model=chunk.model,
            choices=[
                openai.types.chat.chat_completion.Choice(
                    finish_reason=c.finish_reason or "stop",
                    index=c.index,
                    logprobs=c.logprobs,
                    message=openai.types.chat.ChatCompletionMessage(
                        content=c.delta.content or "",
                        role=c.delta.role or "assistant",
                        tool_calls=c.delta.tool_calls,
                    ),
                )
                for c in chunk.choices
            ],
            created=chunk.created,
            object="chat.completion",
        )

    # update the completion choices from the chunk, overwriting or append as necessary

    completion = completion.model_copy()
    choices = []
    for c, chunk_c in zip(completion.choices, chunk.choices):
        c = c.model_copy()
        if chunk_c.finish_reason:
            c.finish_reason = chunk_c.finish_reason
        if chunk_c.index is not None:
            c.index = chunk_c.index
        if chunk_c.logprobs:
            c.logprobs = chunk_c.logprobs
        c.message = openai.types.chat.ChatCompletionMessage(
            content=c.message.content + (chunk_c.delta.content or ""),
            role=chunk_c.delta.role or c.message.role,
            tool_calls=chunk_c.delta.tool_calls or c.message.tool_calls,
        )
        choices.append(c)
    completion.choices = choices
    return completion


class OpenAIStreamHandler(BaseModel):
    callback: Optional[Callable[[Message], None]] = None

    def handle_streaming_chat(self, api_response: openai.Stream) -> Message:
        """
        Accumulate chunk deltas into a full ChatCompletion. Returns the full
        ChatCompletion. Passes a StreamingChatResponse to the callback.
        """
        completion = None
        for chunk in api_response:
            completion = process_streaming_chat_response(
                completion=completion, chunk=chunk
            )
            if self.callback:
                self.callback(StreamingChatResponse(chunk=chunk, completion=completion))
        return completion

    async def handle_streaming_chat_async(self, api_response: openai.Stream) -> Message:
        """
        Accumulate chunk deltas into a full ChatCompletion. Returns the full
        ChatCompletion. Passes a dict of partial ChatCompletions and chunks to
        the callback, if provided.
        """
        completion = None
        async for chunk in api_response:
            completion = process_streaming_chat_response(
                completion=completion, chunk=chunk
            )
            if self.callback:
                self.callback(StreamingChatResponse(chunk=chunk, completion=completion))
        return completion


async def should_fallback(e: NotFoundError, request: ChatRequest) -> bool:
    if (
        "you do not have access" in str(e)
        and request.model.startswith("gpt-4")
        and request.model == marvin.settings.openai.chat.completions.model
    ):
        get_logger().warning(
            "Marvin's default chat model is"
            f" {marvin.settings.openai.chat.completions.model!r}, which your"
            " API key likely does not give you access to. This API call will"
            f" fall back to the {FALLBACK_CHAT_COMPLETIONS_MODEL!r} model. To"
            " avoid this warning, please set"
            " `MARVIN_OPENAI_CHAT_COMPLETIONS_MODEL=<accessible model>` in"
            f" `~/.marvin/.env` - for example, `gpt-3.5-turbo`.\n\n {e}"
        )
        return True
    else:
        return False


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
                inspect.cleandoc(
                    """
                To use Azure OpenAI, please set all of the following environment variables in `~/.marvin/.env`:

                ```
                MARVIN_USE_AZURE_OPENAI=true
                MARVIN_AZURE_OPENAI_API_KEY=...
                MARVIN_AZURE_OPENAI_API_VERSION=...
                MARVIN_AZURE_OPENAI_ENDPOINT=...
                MARVIN_AZURE_OPENAI_DEPLOYMENT_NAME=...
                ```
                """
                )
            )

    api_key = (
        settings.openai.api_key.get_secret_value() if settings.openai.api_key else None
    )
    if not api_key:
        raise ValueError(
            inspect.cleandoc(
                """
            OpenAI API key not found! Marvin will not work properly without it.
            
            You can either:
                1. Set the `MARVIN_OPENAI_API_KEY` or `OPENAI_API_KEY` environment variables
                2. Set `marvin.settings.openai.api_key` in your code (not recommended for production)
                
            If you do not have an OpenAI API key, you can create one at https://platform.openai.com/api-keys.
            """
            )
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
        stream_callback: Optional[Callable[[Message], None]] = None,
        **kwargs: Any,
    ) -> Union["ChatCompletion", T]:
        create: Callable[..., "ChatCompletion"] = (
            completion or self.client.chat.completions.create
        )

        # setup streaming
        if stream_callback is not None:
            kwargs.setdefault("stream", True)

        # validate request
        request = ChatRequest(**kwargs)
        try:
            response: "ChatCompletion" = create(**request.model_dump(exclude_none=True))
        except NotFoundError as e:
            if should_fallback(e, request):
                response = create(
                    **request.model_dump(exclude_none=True)
                    | dict(model=FALLBACK_CHAT_COMPLETIONS_MODEL)
                )
            else:
                raise e

        if request.stream:
            return OpenAIStreamHandler(callback=stream_callback).handle_streaming_chat(
                response
            )
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
        stream_callback: Optional[Callable[[Message], None]] = None,
        **kwargs: Any,
    ) -> Union["ChatCompletion", T]:
        create = self.client.chat.completions.create

        # setup streaming
        if stream_callback is not None:
            kwargs.setdefault("stream", True)

        # validate request
        request = ChatRequest(**kwargs)
        try:
            response: "ChatCompletion" = await create(
                **request.model_dump(exclude_none=True)
            )
        except NotFoundError as e:
            if should_fallback(e, request):
                response = await create(
                    **request.model_dump(exclude_none=True)
                    | dict(model=FALLBACK_CHAT_COMPLETIONS_MODEL)
                )
            else:
                raise e
        if request.stream:
            return await OpenAIStreamHandler(
                callback=stream_callback
            ).handle_streaming_chat_async(response)
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
