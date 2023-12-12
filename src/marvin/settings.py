import os
from contextlib import contextmanager
from typing import Any, Literal, Optional, Union

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MarvinSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="marvin_",
        env_file="~/.marvin/.env",
        extra="allow",
        arbitrary_types_allowed=True,
    )

    def __setattr__(self, name: str, value: Any) -> None:
        """Preserve SecretStr type when setting values."""
        field = self.model_fields.get(name)
        if field:
            annotation = field.annotation
            base_types = (
                getattr(annotation, "__args__", None)
                if getattr(annotation, "__origin__", None) is Union
                else (annotation,)
            )
            if SecretStr in base_types and not isinstance(value, SecretStr):  # type: ignore # noqa: E501
                value = SecretStr(value)
        super().__setattr__(name, value)


class ChatCompletionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="marvin_llm_",
        env_file="~/.marvin/.env",
        extra="allow",
        arbitrary_types_allowed=True,
    )
    model: str = Field(
        description="The default chat model to use.", default="gpt-3.5-turbo"
    )

    @property
    def encoder(self):
        import tiktoken

        return tiktoken.encoding_for_model(self.model).encode


class ImageSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="marvin_image_",
        env_file="~/.marvin/.env",
        extra="allow",
        arbitrary_types_allowed=True,
    )
    model: str = Field(
        default="dall-e-3",
        description="The default image model to use.",
    )
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = Field(
        default="1024x1024",
    )
    response_format: Literal["url", "b64_json"] = Field(default="url")
    style: Literal["vivid", "natural"] = Field(default="vivid")


class SpeechSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="marvin_speech_",
        env_file="~/.marvin/.env",
        extra="allow",
        arbitrary_types_allowed=True,
    )
    model: str = Field(
        default="tts-1-hd",
        description="The default image model to use.",
    )
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = Field(
        default="alloy",
    )
    response_format: Literal["mp3", "opus", "aac", "flac"] = Field(default="mp3")
    speed: float = Field(default=1.0)


class AssistantSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="marvin_llm_",
        env_file="~/.marvin/.env",
        extra="allow",
        arbitrary_types_allowed=True,
    )
    model: str = Field(
        default="gpt-4-1106-preview",
        description="The default assistant model to use.",
    )


class ChatSettings(BaseSettings):
    completions: ChatCompletionSettings = Field(default_factory=ChatCompletionSettings)


class AudioSettings(BaseSettings):
    speech: SpeechSettings = Field(default_factory=SpeechSettings)


class OpenAISettings(BaseSettings):
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


class Settings(BaseSettings):
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
