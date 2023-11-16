import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

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


class MarvinModelSettings(MarvinSettings):
    model: str

    @property
    def encoder(self):
        import tiktoken

        return tiktoken.encoding_for_model(self.model).encode


class ChatCompletionSettings(MarvinModelSettings):
    model: str = Field(
        default="gpt-4-1106-preview",
        description="The default chat model to use.",
    )

    async def acreate(self, **kwargs: Any) -> "ChatCompletion":
        from marvin.settings import settings

        _settings = dict(model=self.model)

        return await settings.openai.async_client.chat.completions.create(
            model=self.model, **kwargs
        )

    def create(self, **kwargs: Any) -> "ChatCompletion":
        from marvin.settings import settings

        return settings.openai.client.chat.completions.create(
            model=self.model, **kwargs
        )


class ImageSettings(MarvinModelSettings):
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
    model: str = Field(
        default="gpt-4-1106-preview",
        description="The default assistant model to use.",
    )


class ChatSettings(MarvinSettings):
    completions: ChatCompletionSettings = Field(default_factory=ChatCompletionSettings)


class AudioSettings(MarvinSettings):
    speech: SpeechSettings = Field(default_factory=SpeechSettings)


class OpenAISettings(MarvinSettings):
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
    Temporarily override Marvin setting values. This will _not_ mutate values that have
    been already been accessed at module load time.

    This function should only be used for testing.
    """
    old_env = os.environ.copy()
    old_settings = settings.model_copy()

    try:
        for setting in kwargs:
            value = kwargs.get(setting)
            if value is not None:
                os.environ[setting] = str(value)
            else:
                os.environ.pop(setting, None)

        new_settings = Settings()

        for field in settings.model_fields:
            object.__setattr__(settings, field, getattr(new_settings, field))

        yield settings
    finally:
        for setting in kwargs:
            value = old_env.get(setting)
            if value is not None:
                os.environ[setting] = value
            else:
                os.environ.pop(setting, None)

        for field in settings.model_fields:
            object.__setattr__(settings, field, getattr(old_settings, field))
