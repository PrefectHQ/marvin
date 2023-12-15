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
from typing import Any, Optional, Union

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Literal


class MarvinSettings(BaseSettings):
    def __setattr__(self, name: str, value: Any) -> None:
        # wrap bare strings in SecretStr if the field is annotated with SecretStr
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


class ChatCompletionSettings(MarvinSettings):
    model_config = SettingsConfigDict(
        env_prefix="marvin_llm_",
        env_file="~/.marvin/.env",
        extra="allow",
        arbitrary_types_allowed=True,
    )
    model: str = Field(
        description="The default chat model to use.", default="gpt-3.5-turbo"
    )

    temperature: float = Field(
        description="The default temperature to use.", default=0.1
    )

    @property
    def encoder(self):
        import tiktoken

        return tiktoken.encoding_for_model(self.model).encode


class ImageSettings(MarvinSettings):
    """Settings for OpenAI's image API.

    Attributes:
        model: The default image model to use, defaults to `dall-e-3`.
        size: The default image size to use, defaults to `1024x1024`.
        response_format: The default response format to use, defaults to `url`.
        style: The default style to use, defaults to `vivid`.
    """

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


class SpeechSettings(MarvinSettings):
    """Settings for OpenAI's speech API.

    Attributes:
        model: The default speech model to use, defaults to `tts-1-hd`.
        voice: The default voice to use, defaults to `alloy`.
        response_format: The default response format to use, defaults to `mp3`.
        speed: The default speed to use, defaults to `1.0`.
    """

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


class AssistantSettings(MarvinSettings):
    """Settings for the assistant API.

    Attributes:
        model: The default assistant model to use, defaults to `gpt-4-1106-preview`.
    """

    model_config = SettingsConfigDict(
        env_prefix="marvin_llm",
        env_file="~/.marvin/.env",
        extra="allow",
        arbitrary_types_allowed=True,
    )

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

    model_config = SettingsConfigDict(
        env_prefix="marvin_openai_",
        env_file="~/.marvin/.env",
        extra="allow",
        arbitrary_types_allowed=True,
    )

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

    model_config = SettingsConfigDict(
        env_prefix="marvin_",
        env_file="~/.marvin/.env",
        extra="allow",
        arbitrary_types_allowed=True,
        protected_namespaces=(),
    )

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

    def set_nested_attr(obj: object, attr_path: str, value: Any):
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
