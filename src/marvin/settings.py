import os
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, Union

from pydantic import ConfigDict, Field, SecretStr, validator, AliasChoices, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(os.getenv("MARVIN_ENV_FILE", "~/.marvin/.env")).expanduser()


class MarvinBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(
        ".env",
        str(Path(os.getenv("MARVIN_ENV_FILE", "~/.marvin/.env")).expanduser()),
    ), env_prefix="MARVIN_", validate_assignment=True)


class OpenAISettings(MarvinBaseSettings):
    """Provider-specific settings. Only some of these will be relevant to users."""
    model_config = ConfigDict(env_prefix="MARVIN_OPENAI_")

    api_key: SecretStr | None = Field(
        None,
        # for OpenAI convenience, we first check the Marvin-specific env var,
        # then the generic one
        validation_alias=AliasChoices("MARVIN_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    organization: str | None = None
    embedding_engine: str = "text-embedding-ada-002"
    api_type: str | None = None
    api_base: str | None = Field(None, description="The endpoint the OpenAI API.")
    api_version: str | None = Field(None, description="The API version")


class AnthropicSettings(MarvinBaseSettings):
    model_config = ConfigDict(env_prefix="MARVIN_ANTHROPIC_")

    api_key: SecretStr | None = None


class AzureOpenAI(MarvinBaseSettings):
    model_config = ConfigDict(env_prefix="MARVIN_AZURE_OPENAI_")

    api_key: SecretStr | None = None
    api_type: Literal["azure", "azure_ad"] = "azure"
    api_base: str | None = Field(
        None,
        description=(
            "The endpoint of the Azure OpenAI API. This should have the form"
            " https://YOUR_RESOURCE_NAME.openai.azure.com"
        ),
    )
    api_version: str = Field("2023-07-01-preview", description="The API version")
    deployment_name: str | None = Field(
        None,
        description=(
            "This will correspond to the custom name you chose for your deployment when"
            " you deployed a model."
        ),
    )


class Settings(MarvinBaseSettings):
    """Marvin settings"""

    home: Path = Path("~/.marvin").expanduser()
    test_mode: bool = False

    # LOGGING
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    verbose: bool = False

    # LLMS
    llm_model: str = "openai/gpt-4"
    llm_max_tokens: int = Field(
        1500, description="The max number of tokens for AI completions"
    )
    llm_max_context_tokens: int = Field(
        3500, description="The max number of tokens to use for context"
    )
    llm_temperature: float = 0.8
    llm_request_timeout_seconds: Union[float, list[float]] = 600.0

    # AI APPLICATIONS
    ai_application_max_iterations: int | None = None

    # providers
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    anthropic: AnthropicSettings = Field(default_factory=AnthropicSettings)
    azure_openai: AzureOpenAI = Field(default_factory=AzureOpenAI)

    # SLACK
    slack_api_token: SecretStr | None = Field(
        None,
        description="The Slack API token to use for the Slack client",
    )

    # TOOLS

    # chroma
    chroma_server_host: str | None = None
    chroma_server_http_port: int | None = None

    # discourse
    discourse_help_category_id: int | None = None
    discourse_api_key: SecretStr | None = None
    discourse_api_username: str | None = None
    discourse_url: str | None = None

    # github
    github_token: SecretStr | None = None

    # wolfram
    wolfram_app_id: SecretStr | None = None

    @model_validator(mode='after')
    def initial_setup(self):
        # print(values)
        # ensure the home directory exists
        # print(values)
        self.home.mkdir(parents=True, exist_ok=True)
        return self

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("log_level", always=True)
    def set_log_level(cls, v):
        import marvin.utilities.logging

        marvin.utilities.logging.setup_logging(level=v)
        return v

    # --- deprecated settings

    @property
    def openai_api_key(self):
        import marvin.utilities.logging

        logger = marvin.utilities.logging.get_logger("Settings")
        logger.warn(
            "`settings.openai_api_key` is deprecated. Use the provider-specific"
            " `settings.openai.api_key` instead."
        )
        return self.openai.api_key

    def __setattr__(self, name, value):
        # handle deprecated setting and forward to correct location
        # this should be a property setter but Pydantic doesn't support it
        if name == "openai_api_key":
            import marvin.utilities.logging

            logger = marvin.utilities.logging.get_logger("Settings")
            logger.warn(
                "`settings.openai_api_key` is deprecated. Use the provider-specific"
                " `settings.openai.api_key` instead."
            )
            # assign to correct location
            self.openai.api_key = value
        else:
            super().__setattr__(name, value)


settings = Settings()


@contextmanager
def temporary_settings(**kwargs):
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
    old_settings = settings.copy()

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
