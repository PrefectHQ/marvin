from pathlib import Path
from typing import ClassVar, Literal, Any, Generator
from contextlib import contextmanager
import os
from pydantic import Field, SecretStr
from .providers import OpenAIBaseSettings, AnthropicBaseSettings, MarvinBaseSettings
from .._compat import model_copy


class Settings(MarvinBaseSettings):
    home: ClassVar[Path] = Path("~/.marvin").expanduser()

    # Provider Settings
    openai: OpenAIBaseSettings = Field(default_factory=OpenAIBaseSettings)
    azure_openai: AnthropicBaseSettings = Field(default_factory=AnthropicBaseSettings)
    anthropic: AnthropicBaseSettings = Field(default_factory=AnthropicBaseSettings)

    # Language Model Settings

    llm_model: str = "openai/gpt-4"

    llm_max_tokens: int = Field(
        default=1500, description="The max number of tokens for AI completions."
    )

    llm_max_context_tokens: int = Field(
        default=3500, description="The max number of tokens to use for context."
    )

    llm_temperature: float = Field(
        default=0.8, description="The temperature to use for AI completions."
    )

    llm_request_timeout_seconds: float | list[float] = 600.0

    # AI Applications
    ai_application_max_iterations: int | None = None

    # Logging Settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    verbose: bool = False

    #################################################################
    ###                   DEPRECATED SETTINGS                     ###
    #################################################################

    # Slack
    slack_api_token: SecretStr | None = Field(
        default=None,
        description="The Slack API token to use for the Slack client",
    )

    # TOOLS

    # chroma
    chroma_server_host: str | None = Field(default=None)

    chroma_server_http_port: int | None = Field(default=None)

    # discourse
    discourse_help_category_id: int | None = Field(default=None)
    discourse_api_key: SecretStr | None = Field(default=None)
    discourse_api_username: str | None = Field(default=None)
    discourse_url: str | None = Field(default=None)

    # github
    github_token: SecretStr | None = Field(default=None)

    # wolfram
    wolfram_app_id: SecretStr | None = Field(default=None)

    def __init__(self, **kwargs: Any) -> None:
        # Hack until fully migrated to Pydantic V2
        super().__init__(**kwargs)
        self.home.mkdir(parents=True, exist_ok=True)

    def __setattr__(self, name: str, value: Any) -> None:
        # Hack until fully migrated to Pydantic V2
        if name == "log_level":
            super().__setattr__(name, value)
            import marvin.utilities.logging  # type: ignore

            marvin.utilities.logging.setup_logging(level=value)
        else:
            super().__setattr__(name, value)


settings = Settings()


@contextmanager
def temporary_settings(**kwargs: Any) -> Generator[Settings, None, None]:
    """
    Temporarily override Marvin setting values. This will _not_ mutate values that have
    been already been accessed at module load time.

    This function should only be used for testing.

    Example:
        >>> from marvin.settings import settings
        >>> with temporary_settings(MARVIN_LLM_MAX_TOKENS=100):
        >>>    assert settings.llm_max_tokens == 100
        >>> assert settings.llm_max_tokens == 1500
    """
    old_env = os.environ.copy()
    old_settings = model_copy(settings)

    try:
        for setting in kwargs:
            value = kwargs.get(setting)
            if value is not None:
                os.environ[setting] = str(value)
            else:
                os.environ.pop(setting, None)

        new_settings = Settings()

        for field in settings.__fields__:
            object.__setattr__(settings, field, getattr(new_settings, field))

        yield settings
    finally:
        for setting in kwargs:
            value = old_env.get(setting)
            if value is not None:
                os.environ[setting] = value
            else:
                os.environ.pop(setting, None)

        for field in settings.__fields__:
            object.__setattr__(settings, field, getattr(old_settings, field))


__all__ = ["settings", "temporary_settings"]
