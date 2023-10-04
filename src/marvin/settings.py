import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal, Optional, Union

from pydantic import Field, SecretStr

from ._compat import BaseSettings, SettingsConfigDict, field_validator

ENV_PATH = Path(os.getenv("MARVIN_ENV_FILE", "~/.marvin/.env")).expanduser()


class MarvinBaseSettings(BaseSettings):
    class Config(SettingsConfigDict):
        env_file = (
            ".env",
            str(Path(os.getenv("MARVIN_ENV_FILE", "~/.marvin/.env")).expanduser()),
        )
        env_prefix = "MARVIN_"
        validate_assignment = True


class OpenAISettings(MarvinBaseSettings):
    """Provider-specific settings. Only some of these will be relevant to users."""

    class Config(MarvinBaseSettings.Config):
        env_prefix = "MARVIN_OPENAI_"
        # extra = "allow"

    api_key: Optional[SecretStr] = Field(
        default=None,
        # for OpenAI convenience, we first check the Marvin-specific env var,
        # then the generic one
        env=["MARVIN_OPENAI_API_KEY", "OPENAI_API_KEY"],
    )
    organization: Optional[str] = Field(default=None)
    embedding_engine: str = Field(default="text-embedding-ada-002", exclude=True)
    api_type: Optional[str] = Field(default=None)
    api_base: Optional[str] = Field(
        default=None, description="The endpoint the OpenAI API."
    )
    api_version: Optional[str] = Field(default=None, description="The API version")

    def get_defaults(self, settings: "Settings") -> dict[str, Any]:
        import os

        import openai

        from marvin import openai as marvin_openai

        response: dict[str, Any] = {}
        if settings.llm_max_context_tokens > 0:
            response["max_tokens"] = settings.llm_max_tokens
        response["api_key"] = self.api_key and self.api_key.get_secret_value()
        if os.environ.get("MARVIN_OPENAI_API_KEY"):
            response["api_key"] = os.environ["MARVIN_OPENAI_API_KEY"]
        if os.environ.get("OPENAI_API_KEY"):
            response["api_key"] = os.environ["OPENAI_API_KEY"]
        if openai.api_key:
            response["api_key"] = openai.api_key
        if marvin_openai.api_key:
            response["api_key"] = marvin_openai.api_key
        response["temperature"] = settings.llm_temperature
        response["request_timeout"] = settings.llm_request_timeout_seconds
        return {k: v for k, v in response.items() if v is not None}


class AnthropicSettings(MarvinBaseSettings):
    class Config(MarvinBaseSettings.Config):
        env_prefix = "MARVIN_ANTHROPIC_"

    api_key: Optional[SecretStr] = Field(
        default=None, env=["MARVIN_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"]
    )

    def get_defaults(self, settings: "Settings") -> dict[str, Any]:
        response: dict[str, Any] = {}
        if settings.llm_max_context_tokens > 0:
            response["max_tokens_to_sample"] = settings.llm_max_tokens
        response["api_key"] = self.api_key and self.api_key.get_secret_value()
        response["temperature"] = settings.llm_temperature
        response["timeout"] = settings.llm_request_timeout_seconds
        if os.environ.get("MARVIN_ANTHROPIC_API_KEY"):
            response["api_key"] = os.environ["MARVIN_ANTHROPIC_API_KEY"]
        if os.environ.get("ANTHROPIC_API_KEY"):
            response["api_key"] = os.environ["ANTHROPIC_API_KEY"]
        return {k: v for k, v in response.items() if v is not None}


class AzureOpenAI(MarvinBaseSettings):
    class Config(MarvinBaseSettings.Config):
        env_prefix = "MARVIN_AZURE_OPENAI_"

    api_key: Optional[SecretStr] = Field(default=None)
    api_type: Literal["azure", "azure_ad"] = "azure"
    api_base: Optional[str] = Field(
        default=None,
        description=(
            "The endpoint of the Azure OpenAI API. This should have the form"
            " https://YOUR_RESOURCE_NAME.openai.azure.com"
        ),
    )
    api_version: Optional[str] = Field(
        default="2023-07-01-preview", description="The API version"
    )
    deployment_name: Optional[str] = Field(
        default=None,
        description=(
            "This will correspond to the custom name you chose for your deployment when"
            " you deployed a model."
        ),
    )

    def get_defaults(self, settings: "Settings") -> dict[str, Any]:
        response: dict[str, Any] = {}
        if settings.llm_max_context_tokens > 0:
            response["max_tokens"] = settings.llm_max_tokens
        response["api_key"] = self.api_key and self.api_key.get_secret_value()
        response["temperature"] = settings.llm_temperature
        response["request_timeout"] = settings.llm_request_timeout_seconds

        import os

        import openai

        from marvin import openai as marvin_openai

        response: dict[str, Any] = {}
        if settings.llm_max_context_tokens > 0:
            response["max_tokens"] = settings.llm_max_tokens
        response["api_key"] = self.api_key and self.api_key.get_secret_value()
        if os.environ.get("MARVIN_AZURE_OPENAI_API_KEY"):
            response["api_key"] = os.environ["MARVIN_AZURE_OPENAI_API_KEY"]
        if openai.api_key:
            response["api_key"] = openai.api_key
        if marvin_openai.api_key:
            response["api_key"] = marvin_openai.api_key
        return {k: v for k, v in response.items() if v is not None}


class Settings(MarvinBaseSettings):
    """Marvin settings"""

    home: Path = Path("~/.marvin").expanduser()
    test_mode: bool = False

    # LOGGING
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    verbose: bool = False

    # LLMS
    llm_model: str = "openai/gpt-3.5-turbo"
    llm_max_tokens: int = Field(
        default=1500, description="The max number of tokens for AI completions"
    )
    llm_max_context_tokens: int = Field(
        default=3500, description="The max number of tokens to use for context"
    )
    llm_temperature: float = Field(default=0.8)
    llm_request_timeout_seconds: Union[float, list[float]] = 600.0

    # AI APPLICATIONS
    ai_application_max_iterations: Optional[int] = None

    # providers
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    anthropic: AnthropicSettings = Field(default_factory=AnthropicSettings)
    azure_openai: AzureOpenAI = Field(default_factory=AzureOpenAI)

    # SLACK
    slack_api_token: Optional[SecretStr] = Field(
        default=None,
        description="The Slack API token to use for the Slack client",
    )

    # TOOLS

    # chroma
    chroma_server_host: Optional[str] = Field(default=None)
    chroma_server_http_port: Optional[int] = Field(default=None)

    # discourse
    discourse_help_category_id: Optional[int] = Field(default=None)
    discourse_api_key: Optional[SecretStr] = Field(default=None)
    discourse_api_username: Optional[str] = Field(default=None)
    discourse_url: Optional[str] = Field(default=None)

    # github
    github_token: Optional[SecretStr] = Field(default=None)

    # wolfram
    wolfram_app_id: Optional[SecretStr] = Field(default=None)

    @field_validator("home")
    @classmethod
    def initial_setup(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v

    def get_defaults(self, provider: Optional[str] = None) -> dict[str, Any]:
        response: dict[str, Any] = {}
        if provider == "openai":
            return self.openai.get_defaults(self)
        elif provider == "anthropic":
            return self.anthropic.get_defaults(self)
        elif provider == "azure_openai":
            return self.azure_openai.get_defaults(self)
        else:
            return response


settings = Settings()


@contextmanager
def temporary_settings(**kwargs: Any):
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
