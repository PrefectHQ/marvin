"""Settings for configuring `marvin`."""

import os
from contextlib import contextmanager
from copy import deepcopy
from typing import Any, Callable, Literal, Optional, Union

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MarvinSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="" if os.getenv("MARVIN_TEST_MODE") else ("~/.marvin/.env", ".env"),
        extra="allow",
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

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
        env_prefix="marvin_chat_completions_", extra="ignore"
    )
    model: str = Field(
        description="The default chat model to use.", default="gpt-4-1106-preview"
    )

    temperature: float = Field(description="The default temperature to use.", default=1)

    @property
    def encoder(self):
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

        return encoding.encode


class ChatVisionSettings(MarvinSettings):
    model_config = SettingsConfigDict(env_prefix="marvin_chat_vision_", extra="ignore")
    model: str = Field(
        description="The default vision model to use.", default="gpt-4-vision-preview"
    )
    temperature: float = Field(description="The default temperature to use.", default=1)
    max_tokens: int = 500

    @property
    def encoder(self):
        import tiktoken

        return tiktoken.encoding_for_model(self.model).encode


class ChatSettings(MarvinSettings):
    model_config = SettingsConfigDict(env_prefix="marvin_chat_", extra="ignore")
    completions: ChatCompletionSettings = Field(default_factory=ChatCompletionSettings)
    vision: ChatVisionSettings = Field(default_factory=ChatVisionSettings)


class ImageSettings(MarvinSettings):
    """Settings for OpenAI's image API.

    Attributes:
        model: The default image model to use, defaults to `dall-e-3`.
        size: The default image size to use, defaults to `1024x1024`.
        response_format: The default response format to use, defaults to `url`.
        style: The default style to use, defaults to `vivid`.
    """

    model_config = SettingsConfigDict(env_prefix="marvin_image_", extra="ignore")

    model: str = Field(
        default="dall-e-3",
        description="The default image model to use.",
    )
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = Field(
        default="1024x1024",
    )
    response_format: Literal["url", "b64_json"] = Field(
        default="url",
        description=(
            "URLs only last for one hour and must be downloaded within that time."
            " b64_json returns a base64-encoded JSON object containing the image."
        ),
    )
    style: Literal["vivid", "natural"] = Field(default="vivid")
    quality: Literal["standard", "hd"] = Field(default="standard")


class SpeechSettings(MarvinSettings):
    """Settings for OpenAI's speech API.

    Attributes:
        model: The default speech model to use, defaults to `tts-1-hd`.
        voice: The default voice to use, defaults to `echo`.
        response_format: The default response format to use, defaults to `mp3`.
        speed: The default speed to use, defaults to `1.0`.
    """

    model_config = SettingsConfigDict(
        env_prefix="marvin_speech_",
        extra="ignore",
    )

    model: str = Field(
        default="tts-1-hd",
        description="The default model to use.",
    )
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = Field(
        default="echo",
    )
    response_format: Literal["mp3", "opus", "aac", "flac"] = Field(default="mp3")
    speed: float = Field(default=1.0)


class AssistantSettings(MarvinSettings):
    """Settings for the assistant API.

    Attributes:
        model: The default assistant model to use, defaults to `gpt-4-1106-preview`.
    """

    model_config = SettingsConfigDict(env_prefix="marvin_assistant_")

    model: str = Field(
        default="gpt-4-1106-preview",
        description="The default assistant model to use.",
    )


class AudioSettings(MarvinSettings):
    """Settings for the audio API."""

    model_config = SettingsConfigDict(env_prefix="marvin_audio_", extra="ignore")

    speech: SpeechSettings = Field(default_factory=SpeechSettings)


class OpenAISettings(MarvinSettings):
    """Settings for the OpenAI API.


    Attributes:
        api_key: Your OpenAI API key.
        organization: Your OpenAI organization ID.
        llms: Settings for the chat API.
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
        extra="ignore",
    )

    api_key: Optional[SecretStr] = Field(
        default=None,
        description="Your OpenAI API key.",
    )

    organization: Optional[str] = Field(
        default=None,
        description="Your OpenAI organization ID.",
    )

    base_url: Optional[str] = Field(
        default=None,
        description="Your OpenAI base URL.",
    )

    chat: ChatSettings = Field(default_factory=ChatSettings)
    images: ImageSettings = Field(default_factory=ImageSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    assistants: AssistantSettings = Field(default_factory=AssistantSettings)

    @field_validator("api_key", mode="before")
    def discover_api_key(cls, v):
        if v is None:
            # check global OpenAI API key
            v = os.environ.get("OPENAI_API_KEY")

        return v


class TextAISettings(MarvinSettings):
    model_config = SettingsConfigDict(env_prefix="marvin_ai_text_", extra="ignore")
    generate_cache_token_cap: int = Field(600)


class AISettings(MarvinSettings):
    model_config = SettingsConfigDict(env_prefix="marvin_ai_", extra="ignore")

    text: TextAISettings = Field(default_factory=TextAISettings)


def default_post_processor_fn(response):
    return response


class Settings(MarvinSettings):
    """Settings for `marvin`.

    This is the main settings object for `marvin`.

    Attributes:
        openai: Settings for the OpenAI API.
        log_level: The log level to use, defaults to `INFO`.

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
        protected_namespaces=(),
    )

    post_processor_fn: Optional[Callable] = default_post_processor_fn

    # providers
    provider: Literal["openai", "azure_openai"] = Field(
        default="openai",
        description=(
            'The LLM provider to use. Supports "openai" and "azure_openai" at this'
            " time."
        ),
    )
    openai: OpenAISettings = Field(default_factory=OpenAISettings)

    # ai settings
    ai: AISettings = Field(default_factory=AISettings)

    # beta settings
    auto_import_beta_modules: bool = Field(
        True,
        description="If True, the marvin.beta module will be automatically imported when marvin is imported.",
    )

    # log settings
    log_level: str = Field(
        default="INFO",
        description="The log level to use.",
    )

    log_verbose: bool = Field(
        default=False,
        description=(
            "Whether to log verbose messages, such as full API requests and responses."
        ),
    )

    @field_validator("log_level", mode="after")
    @classmethod
    def set_log_level(cls, v):
        from marvin.utilities.logging import setup_logging

        setup_logging(level=v)
        return v


settings = Settings()


@contextmanager
def temporary_settings(**kwargs: Any):
    """
    Temporarily override Marvin setting values, including nested settings objects.

    To override nested settings, use `__` to separate nested attribute names.

    Args:
        **kwargs: The settings to override, including nested settings.

    Example:
        Temporarily override log level and OpenAI API key:
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
