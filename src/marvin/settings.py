import os
from contextlib import contextmanager
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatCompletionSettings(BaseModel):
    model: str = Field(
        default="gpt-4-1106-preview",
        description="The default chat model to use.",
    )

    model_config = ConfigDict(
        extra="allow",
        arbitrary_types_allowed=True,
    )


class ChatSettings(BaseSettings):
    completions: ChatCompletionSettings = Field(default_factory=ChatCompletionSettings)


class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="marvin_openai_", env_file="~/.marvin/.env"
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
