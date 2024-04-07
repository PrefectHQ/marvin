import io
from functools import partial
from pathlib import Path
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Callable,
    Optional,
    TypeVar,
    Union,
)

import openai
import openai.types.audio
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
    TranscriptRequest,
    VisionRequest,
)
from marvin.utilities.asyncio import run_sync
from marvin.utilities.logging import get_logger
from marvin.utilities.openai import get_openai_client

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
            " `MARVIN_CHAT_COMPLETIONS_MODEL=<accessible model>` in"
            f" `~/.marvin/.env` - for example, `gpt-3.5-turbo`.\n\n {e}"
        )
        return True
    else:
        return False


class MarvinClient(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True, protected_namespaces=()
    )

    client: Client = pydantic.Field(
        default_factory=lambda: get_openai_client(is_async=False)
    )

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
            if run_sync(should_fallback(e, request)):
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

    def generate_transcript(
        self, file: Union[Path, IO[bytes]], **kwargs: Any
    ) -> openai.types.audio.Transcription:
        request = TranscriptRequest(**kwargs)
        validated_kwargs = request.model_dump(exclude_none=True)
        if isinstance(file, (Path, str)):
            with open(file, "rb") as f:
                response = self.client.audio.transcriptions.create(
                    file=f, **validated_kwargs
                )
        # bytes or a file handler were provided
        else:
            if isinstance(file, bytes):
                file = io.BytesIO(file)
                file.name = "audio.mp3"

            response = self.client.audio.transcriptions.create(
                file=file, **validated_kwargs
            )
        return response


class AsyncMarvinClient(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True, protected_namespaces=()
    )

    client: AsyncClient = pydantic.Field(
        default_factory=lambda: get_openai_client(is_async=True)
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
            if await should_fallback(e, request):
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

    async def generate_speech(
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

    async def generate_transcript(self, file: Union[Path, IO[bytes]], **kwargs: Any):
        request = TranscriptRequest(**kwargs)
        validated_kwargs = request.model_dump(exclude_none=True)
        if isinstance(file, (Path, str)):
            with open(file, "rb") as f:
                response = await self.client.audio.transcriptions.create(
                    file=f, **validated_kwargs
                )
        # bytes or a file handler were provided
        else:
            if isinstance(file, bytes):
                file = io.BytesIO(file)
                file.name = "audio.mp3"

            response = await self.client.audio.transcriptions.create(
                file=file, **validated_kwargs
            )
        return response


def get_default_client(**client_kwargs) -> MarvinClient:
    client_cls = marvin.settings.default_client or MarvinClient
    return client_cls(**client_kwargs)


def get_default_async_client(**client_kwargs) -> AsyncMarvinClient:
    client_cls = marvin.settings.default_async_client or AsyncMarvinClient
    return client_cls(**client_kwargs)
