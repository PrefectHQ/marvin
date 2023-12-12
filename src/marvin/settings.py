"""Settings for configuring `marvin`.

## Requirements
All you ***need*** to configure is your OpenAI API key.

You can set this in `~/.marvin/.env` or as an environment variable on your system:
```
MARVIN_OPENAI_API_KEY=sk-...
```
---
"""
import os
from contextlib import contextmanager
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Optional, Union

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Literal

if TYPE_CHECKING:
    from openai import AsyncClient, Client
    from openai._base_client import HttpxBinaryResponseContent
    from openai.types.chat import ChatCompletion
    from openai.types.images_response import ImagesResponse


class MarvinSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="marvin_",
        env_file="~/.marvin/.env",
        extra="allow",
        arbitrary_types_allowed=True,
    )

    def __setattr__(self, name: str, value: Any) -> None:
        field = self.model_fields.get(name)
        if field:
            annotation = field.annotation
            base_types = (
                annotation.__args__
                if getattr(annotation, "__origin__", None) is Union
                else (annotation,)
            )
            if SecretStr in base_types and not isinstance(value, SecretStr):
                value = SecretStr(value)
        super().__setattr__(name, value)


class MarvinModelSettings(MarvinSettings):
    model: str

    @property
    def encoder(self):
        import tiktoken

        return tiktoken.encoding_for_model(self.model).encode


class ChatCompletionSettings(MarvinModelSettings):
    """Settings for chat completions.

    Attributes:
        model: The default chat model to use, defaults to `gpt-3.5-turbo-1106`.


    Example:
        Set the current chat model to `gpt-4-1106-preview`:
        ```python
        import marvin

        marvin.settings.openai.chat.completions.model = "gpt-4-1106-preview"

        assert marvin.settings.openai.chat.completions.model == "gpt-4-1106-preview"
        ```
    """

    model: str = Field(
        default="gpt-3.5-turbo-1106",
        description="The default chat model to use.",
    )

    async def acreate(self, **kwargs: Any) -> "ChatCompletion":
        from marvin.settings import settings

        return await settings.openai.async_client.chat.completions.create(
            model=self.model, **kwargs
        )

    def create(self, **kwargs: Any) -> "ChatCompletion":
        from marvin.settings import settings

        return settings.openai.client.chat.completions.create(
            model=self.model, **kwargs
        )


class ImageSettings(MarvinModelSettings):
    """Settings for OpenAI's image API.

    Attributes:
        model: The default image model to use, defaults to `dall-e-3`.
        size: The default image size to use, defaults to `1024x1024`.
        response_format: The default response format to use, defaults to `url`.
        style: The default style to use, defaults to `vivid`.
    """

    model: str = Field(
        default="dall-e-3",
        description="The default image model to use.",
    )
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = Field(
        default="1024x1024",
    )
    response_format: Literal["url", "b64_json"] = Field(default="url")
    style: Literal["vivid", "natural"] = Field(default="vivid")

    async def agenerate(self, prompt: str, **kwargs: Any) -> "ImagesResponse":
        from marvin.settings import settings

        return await settings.openai.async_client.images.generate(
            model=self.model,
            prompt=prompt,
            size=self.size,
            response_format=self.response_format,
            style=self.style,
            **kwargs,
        )

    def generate(self, prompt: str, **kwargs: Any) -> "ImagesResponse":
        from marvin.settings import settings

        return settings.openai.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=self.size,
            response_format=self.response_format,
            style=self.style,
            **kwargs,
        )


class SpeechSettings(MarvinModelSettings):
    """Settings for OpenAI's speech API.

    Attributes:
        model: The default speech model to use, defaults to `tts-1-hd`.
        voice: The default voice to use, defaults to `alloy`.
        response_format: The default response format to use, defaults to `mp3`.
        speed: The default speed to use, defaults to `1.0`.
    """

    model: str = Field(
        default="tts-1-hd",
        description="The default image model to use.",
    )
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = Field(
        default="alloy",
    )
    response_format: Literal["mp3", "opus", "aac", "flac"] = Field(default="mp3")
    speed: float = Field(default=1.0)

    async def acreate(self, input: str, **kwargs: Any) -> "HttpxBinaryResponseContent":
        from marvin.settings import settings

        return await settings.openai.async_client.audio.speech.create(
            model=kwargs.get("model", self.model),
            input=input,
            voice=kwargs.get("voice", self.voice),
            response_format=kwargs.get("response_format", self.response_format),
            speed=kwargs.get("speed", self.speed),
        )

    def create(self, input: str, **kwargs: Any) -> "HttpxBinaryResponseContent":
        from marvin.settings import settings

        return settings.openai.client.audio.speech.create(
            model=kwargs.get("model", self.model),
            input=input,
            voice=kwargs.get("voice", self.voice),
            response_format=kwargs.get("response_format", self.response_format),
            speed=kwargs.get("speed", self.speed),
        )


class AssistantSettings(MarvinModelSettings):
    """Settings for the assistant API.

    Attributes:
        model: The default assistant model to use, defaults to `gpt-4-1106-preview`.
    """

    model: str = Field(
        default="gpt-4-1106-preview",
        description="The default assistant model to use.",
    )


class ChatSettings(MarvinSettings):
    completions: ChatCompletionSettings = Field(default_factory=ChatCompletionSettings)


class AudioSettings(MarvinSettings):
    speech: SpeechSettings = Field(default_factory=SpeechSettings)


class OpenAISettings(MarvinSettings):
    """Settings for the OpenAI API.


    Attributes:
        api_key: Your OpenAI API key.
        organization: Your OpenAI organization ID.
        chat: Settings for the chat API.
        images: Settings for the images API.
        audio: Settings for the audio API.
        assistants: Settings for the assistants API.

    Example:
        Set the OpenAI API key:
        ```python
        import marvin

        marvin.settings.openai.api_key = "sk-..."

        assert marvin.settings.openai.api_key.get_secret_value() == "sk-..."
        ```
    """

    model_config = SettingsConfigDict(env_prefix="marvin_openai_")

    api_key: Optional[SecretStr] = Field(
        default=None,
        description="Your OpenAI API key.",
    )

    organization: Optional[str] = Field(
        default=None,
        description="Your OpenAI organization ID.",
    )

    chat: ChatSettings = Field(default_factory=ChatSettings)
    images: ImageSettings = Field(default_factory=ImageSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    assistants: AssistantSettings = Field(default_factory=AssistantSettings)

    @property
    def async_client(
        self, api_key: Optional[str] = None, **kwargs: Any
    ) -> "AsyncClient":
        from openai import AsyncClient

        if not (api_key or self.api_key):
            raise ValueError("No API key provided.")
        elif not api_key and self.api_key:
            api_key = self.api_key.get_secret_value()

        return AsyncClient(
            api_key=api_key,
            organization=self.organization,
            **kwargs,
        )

    @property
    def client(self, api_key: Optional[str] = None, **kwargs: Any) -> "Client":
        from openai import Client

        if not (api_key or self.api_key):
            raise ValueError("No API key provided.")
        elif not api_key and self.api_key:
            api_key = self.api_key.get_secret_value()

        return Client(
            api_key=api_key,
            organization=self.organization,
            **kwargs,
        )


class Settings(MarvinSettings):
    """Settings for `marvin`.

    This is the main settings object for `marvin`.

    Attributes:
        openai: Settings for the OpenAI API.
        log_level: The log level to use, defaults to `DEBUG`.

    Example:
        Set the log level to `INFO`:
        ```python
        import marvin

        marvin.settings.log_level = "INFO"

        assert marvin.settings.log_level == "INFO"
        ```
    """

    model_config = SettingsConfigDict(env_prefix="marvin_")

    openai: OpenAISettings = Field(default_factory=OpenAISettings)

    log_level: str = Field(
        default="DEBUG",
        description="The log level to use.",
    )


settings = Settings()


@contextmanager
def temporary_settings(**kwargs: Any):
    """
    Temporarily override Marvin setting values, including nested settings objects.

    To override nested settings, use `__` to separate nested attribute names.

    Args:
        **kwargs: The settings to override, including nested settings.

    Example:
        Temporarily override the OpenAI API key:
        ```python
        import marvin
        from marvin.settings import temporary_settings

        # Override top-level settings
        with temporary_settings(log_level="INFO"):
            assert marvin.settings.log_level == "INFO"
        assert marvin.settings.log_level == "DEBUG"

        # Override nested settings
        with temporary_settings(openai__api_key="new-api-key"):
            assert marvin.settings.openai.api_key.get_secret_value() == "new-api-key"
        assert marvin.settings.openai.api_key.get_secret_value().startswith("sk-")
        ```
    """
    old_env = os.environ.copy()
    old_settings = deepcopy(settings)

    def set_nested_attr(obj, attr_path: str, value: Any):
        parts = attr_path.split("__")
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)

    try:
        for attr_path, value in kwargs.items():
            set_nested_attr(settings, attr_path, value)
        yield

    finally:
        os.environ.clear()
        os.environ.update(old_env)

        for attr, value in old_settings:
            set_nested_attr(settings, attr, value)
