import base64
import datetime
from pathlib import Path
from typing import Any, Callable, Generic, Literal, Optional, TypeVar, Union

import openai.types.chat
from openai.types.chat import ChatCompletion
from pydantic import BaseModel, Field, PrivateAttr, computed_field
from typing_extensions import Annotated, Self

from marvin.settings import settings

T = TypeVar("T", bound=BaseModel)

# OpenAI client 1.8 moved the HttpxBinaryResponseContent class to a different
# module, presumably this will continue to change in the future
try:
    # >= 1.8
    from openai._legacy_response import HttpxBinaryResponseContent  # noqa F401
except ImportError:
    # < 1.8
    from openai._base_client import HttpxBinaryResponseContent  # noqa F401


class ResponseFormat(BaseModel):
    type: str


LogitBias = dict[str, float]


class MarvinType(BaseModel):
    # by default, mavin types are not allowed to have extra fields
    # because they are used for validation throughout the codebase
    model_config = dict(extra="forbid")


class Function(MarvinType, Generic[T]):
    name: str
    description: Optional[str]
    parameters: dict[str, Any]

    model: Optional[type[T]] = Field(default=None, exclude=True, repr=False)

    # Private field that holds the executable function, if available
    _python_fn: Optional[Callable[..., Any]] = PrivateAttr(default=None)

    def validate_json(self: Self, json_data: Union[str, bytes, bytearray]) -> T:
        if self.model is None:
            raise ValueError("This Function was not initialized with a model.")
        return self.model.model_validate_json(json_data)

    @classmethod
    def create(
        cls, *, _python_fn: Optional[Callable[..., Any]] = None, **kwargs: Any
    ) -> "Function":
        instance = cls(**kwargs)
        if _python_fn is not None:
            instance._python_fn = _python_fn
        return instance


class Tool(MarvinType):
    type: str


class FunctionTool(Tool, Generic[T]):
    function: Optional[Function[T]] = None


class ToolSet(MarvinType, Generic[T]):
    tools: Optional[list[Union[Tool, FunctionTool[T]]]] = None
    tool_choice: Optional[Union[Literal["auto"], dict[str, Any]]] = None


class RetrievalTool(FunctionTool[T]):
    type: Literal["retrieval"] = "retrieval"


class CodeInterpreterTool(FunctionTool[T]):
    type: Literal["code_interpreter"] = "code_interpreter"


class FunctionCall(MarvinType):
    name: str


class ImageUrl(MarvinType):
    url: str = Field(
        description="URL of the image to be sent or a base64 encoded image."
    )
    detail: str = "auto"


class ImageFileContentBlock(MarvinType):
    """Schema for messages containing images"""

    type: Literal["image_url"] = "image_url"
    image_url: ImageUrl


class TextContentBlock(MarvinType):
    """Schema for messages containing text"""

    type: Literal["text"] = "text"
    text: str


class BaseMessage(MarvinType):
    """Base schema for messages"""

    content: Union[str, list[Union[ImageFileContentBlock, TextContentBlock]]]
    role: str


class Grammar(MarvinType):
    logit_bias: Optional[LogitBias] = None
    max_tokens: Optional[Annotated[int, Field(strict=True, ge=1)]] = None
    response_format: Optional[ResponseFormat] = None


class Prompt(Grammar, ToolSet[T], Generic[T]):
    messages: list[BaseMessage] = Field(default_factory=list)


class ResponseModel(MarvinType):
    model: type
    name: str = Field(default="FormatResponse")
    description: str = Field(default="Response format")


class ChatRequest(Prompt[T]):
    model: str = Field(default_factory=lambda: settings.openai.chat.completions.model)
    frequency_penalty: Optional[
        Annotated[float, Field(strict=True, ge=-2.0, le=2.0)]
    ] = 0
    n: Optional[Annotated[int, Field(strict=True, ge=1)]] = 1
    presence_penalty: Optional[
        Annotated[float, Field(strict=True, ge=-2.0, le=2.0)]
    ] = 0
    seed: Optional[int] = None
    stop: Optional[Union[str, list[str]]] = None
    stream: Optional[bool] = False
    temperature: Optional[Annotated[float, Field(strict=True, ge=0, le=2)]] = Field(
        default_factory=lambda: settings.openai.chat.completions.temperature
    )
    top_p: Optional[Annotated[float, Field(strict=True, ge=0, le=1)]] = 1
    user: Optional[str] = None


class VisionRequest(MarvinType):
    messages: list[BaseMessage] = Field(default_factory=list)
    model: str = Field(default_factory=lambda: settings.openai.chat.vision.model)
    logit_bias: Optional[LogitBias] = None
    max_tokens: Optional[Annotated[int, Field(strict=True, ge=1)]] = Field(
        default_factory=lambda: settings.openai.chat.vision.max_tokens
    )
    frequency_penalty: Optional[
        Annotated[float, Field(strict=True, ge=-2.0, le=2.0)]
    ] = 0
    n: Optional[Annotated[int, Field(strict=True, ge=1)]] = 1
    presence_penalty: Optional[
        Annotated[float, Field(strict=True, ge=-2.0, le=2.0)]
    ] = 0
    seed: Optional[int] = None
    stop: Optional[Union[str, list[str]]] = None
    stream: Optional[bool] = False
    temperature: Optional[Annotated[float, Field(strict=True, ge=0, le=2)]] = Field(
        default_factory=lambda: settings.openai.chat.vision.temperature
    )
    top_p: Optional[Annotated[float, Field(strict=True, ge=0, le=1)]] = 1
    user: Optional[str] = None


class TranscriptRequest(MarvinType):
    model: Literal["whisper-1"] = "whisper-1"
    prompt: Optional[str] = Field(
        None,
        description=(
            "An optional prompt to guide the transcription. Useful for setting tone,"
            " supplying spelling of complex words, including filler vocalizations, etc."
        ),
    )
    response_format: Optional[
        Literal["json", "text", "srt", "verbose_json", "vtt"]
    ] = None
    language: Optional[str] = None
    temperature: Optional[float] = None


class ChatResponse(MarvinType):
    model_config = dict(arbitrary_types_allowed=True)
    request: Union[ChatRequest, VisionRequest]
    response: ChatCompletion
    tool_outputs: list[Any] = []


class ImageRequest(MarvinType):
    prompt: str
    model: Optional[str] = Field(default_factory=lambda: settings.openai.images.model)

    n: Optional[int] = 1
    quality: Optional[Literal["standard", "hd"]] = Field(
        default_factory=lambda: settings.openai.images.quality
    )
    response_format: Optional[Literal["url", "b64_json"]] = Field(
        default_factory=lambda: settings.openai.images.response_format
    )
    size: Optional[
        Literal["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"]
    ] = Field(default_factory=lambda: settings.openai.images.size)
    style: Optional[Literal["vivid", "natural"]] = Field(
        default_factory=lambda: settings.openai.images.style
    )


class SpeechRequest(MarvinType):
    input: str
    model: Literal["tts-1", "tts-1-hd"] = Field(
        default_factory=lambda: settings.openai.audio.speech.model
    )
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = Field(
        default_factory=lambda: settings.openai.audio.speech.voice
    )
    response_format: Optional[Literal["mp3", "opus", "aac", "flac"]] = Field(
        default_factory=lambda: settings.openai.audio.speech.response_format
    )
    speed: Optional[float] = Field(
        default_factory=lambda: settings.openai.audio.speech.speed
    )


class AssistantMessage(BaseMessage):
    id: str
    thread_id: str
    created_at: int
    assistant_id: Optional[str] = None
    run_id: Optional[str] = None
    file_ids: list[str] = []
    metadata: dict[str, Any] = {}


class Run(MarvinType, Generic[T]):
    id: str
    thread_id: str
    created_at: int
    status: str
    model: str
    instructions: Optional[str]
    tools: Optional[list[FunctionTool[T]]] = None
    metadata: dict[str, str]


class StreamingChatResponse(MarvinType):
    chunk: openai.types.chat.ChatCompletionChunk = Field(
        description="The most recently-received chunk of the response"
    )
    completion: openai.types.chat.ChatCompletion = Field(
        description=(
            "The reconstructed completion object, through the most recently-received"
            " chunk"
        )
    )

    @computed_field
    @property
    def messages(self) -> list[BaseMessage]:
        return [c.message for c in self.completion.choices]


class Image(MarvinType):
    data: Optional[bytes] = Field(default=None, repr=False)
    url: Optional[str] = None
    format: str = "png"
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    detail: Literal["auto", "low", "high"] = "auto"

    def __init__(self, data_or_url=None, **kwargs):
        if data_or_url is not None:
            obj = type(self).infer(data_or_url, **kwargs)
            super().__init__(**obj.model_dump())
        else:
            super().__init__(**kwargs)

    @classmethod
    def infer(cls, data_or_url=None, **kwargs):
        if isinstance(data_or_url, bytes):
            return cls(data=data_or_url, **kwargs)
        elif isinstance(data_or_url, (str, Path)):
            path = Path(data_or_url)
            if path.exists():
                return cls.from_path(path, **kwargs)
            else:
                return cls(url=data_or_url, **kwargs)
        else:
            return cls(**kwargs)

    @classmethod
    def from_path(cls, path: Union[str, Path]) -> "Image":
        with open(path, "rb") as f:
            data = f.read()
        format = path.split(".")[-1]
        if format not in ["jpg", "jpeg", "png", "webm"]:
            raise ValueError("Invalid audio format")
        return cls(data=data, url=path, format=format)

    @classmethod
    def from_url(cls, url: str) -> "Image":
        return cls(url=url)

    def to_message_content(self) -> ImageFileContentBlock:
        if self.url:
            return ImageFileContentBlock(
                image_url=dict(url=self.url, detail=self.detail)
            )
        elif self.data:
            b64_image = base64.b64encode(self.data).decode("utf-8")
            path = f"data:image/{self.format};base64,{b64_image}"
            return ImageFileContentBlock(image_url=dict(url=path, detail=self.detail))
        else:
            raise ValueError("Image source is not specified")

    def save(self, path: Union[str, Path]):
        if self.data is None:
            raise ValueError("No image data to save")
        if isinstance(path, str):
            path = Path(path)
        with path.open("wb") as f:
            f.write(self.data)


class Audio(MarvinType):
    data: bytes = Field(repr=False)
    url: Optional[Path] = None
    format: Literal["mp3", "wav"] = "mp3"
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @classmethod
    def from_path(cls, path: Union[str, Path]) -> "Audio":
        with open(path, "rb") as f:
            data = f.read()
        format = path.split(".")[-1]
        if format not in ["mp3", "wav"]:
            raise ValueError("Invalid audio format")
        return cls(data=data, url=path, format=format)

    def save(self, path: str):
        with open(path, "wb") as f:
            f.write(self.data)

    def play(self):
        import marvin.audio

        marvin.audio.play_audio(self.data)
