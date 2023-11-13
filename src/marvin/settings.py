import os
from contextlib import contextmanager
from typing import Any, Optional, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import partial

if TYPE_CHECKING:
    from openai import AsyncClient


class ChatCompletionSettings(BaseModel):
    model: str = Field(
        default="gpt-4-1106-preview",
        description="The default chat model to use.",
    )

    model_config = ConfigDict(
        extra="allow",
        arbitrary_types_allowed=True,
    )

    def acreate(self, **kwargs: Any) -> Any:
        from marvin.settings import settings

        return partial(
            settings.openai.client.chat.completions.create,
            **kwargs | self.model_dump(),
        )

    @property
    def encoder(self):
        import tiktoken

        return tiktoken.encoding_for_model(self.model).encode


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

    @property
    def client(self, api_key: Optional[str] = None, **kwargs: Any) -> "AsyncClient":
        from openai import AsyncClient

        return AsyncClient(
            api_key=api_key or self.api_key.get_secret_value(),
            organization=self.organization,
            **kwargs,
        )


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
