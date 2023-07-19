import os
from pathlib import Path
from typing import Literal, Union

from pydantic import BaseSettings, Field, SecretStr, root_validator, validator


class MarvinBaseSettings(BaseSettings):
    class Config:
        env_file = (
            ".env",
            str(Path(os.getenv("MARVIN_ENV_FILE", "~/.marvin/.env")).expanduser()),
        )
        env_prefix = "MARVIN_"
        validate_assignment = True


class OpenAISettings(MarvinBaseSettings):
    """Provider-specific settings. Only some of these will be relevant to users."""

    class Config:
        env_prefix = "MARVIN_OPENAI_"

    api_key: SecretStr = Field(
        None,
        # for OpenAI convenience, we first check the Marvin-specific env var,
        # then the generic one
        env=["MARVIN_OPENAI_API_KEY", "OPENAI_API_KEY"],
    )
    organization: str = Field(None)
    api_base: str = None
    embedding_engine: str = "text-embedding-ada-002"

    @validator("api_key", always=True)
    def set_api_key(cls, v):
        if v is not None:
            import openai

            openai.api_key = v.get_secret_value()
        return v


class AnthropicSettings(MarvinBaseSettings):
    class Config:
        env_prefix = "MARVIN_ANTHROPIC_"

    api_key: SecretStr = None


class Settings(MarvinBaseSettings):
    """Marvin settings"""

    home: Path = Path("~/.marvin").expanduser()
    test_mode: bool = False

    # LOGGING
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    verbose: bool = False

    # LLMS
    llm_model: str = "gpt-3.5-turbo"
    llm_max_tokens: int = Field(
        1500, description="The max number of tokens for AI completions"
    )
    llm_max_context_tokens: int = Field(
        3500, description="The max number of tokens to use for context"
    )
    llm_temperature: float = 0.8
    llm_request_timeout_seconds: Union[float, list[float]] = 600.0

    # AI APPLICATIONS
    ai_application_max_iterations: int = None

    # providers
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    anthropic: AnthropicSettings = Field(default_factory=AnthropicSettings)

    # SLACK
    slack_api_token: SecretStr = Field(
        None,
        description="The Slack API token to use for the Slack client",
    )

    # TOOLS

    # chroma
    chroma_server_host: str = Field(None)
    chroma_server_http_port: int = Field(None)

    # discourse
    discourse_help_category_id: int = Field(None)
    discourse_api_key: SecretStr = Field(None)
    discourse_api_username: str = Field(None)
    discourse_url: str = Field(None)

    # github
    github_token: SecretStr = Field(None)

    # wolfram
    wolfram_app_id: SecretStr = Field(None)

    @root_validator
    def initial_setup(cls, values):
        # ensure the home directory exists
        values["home"].mkdir(parents=True, exist_ok=True)
        return values

    @validator("log_level", always=True)
    def set_log_level(cls, v):
        import marvin.utilities.logging

        marvin.utilities.logging.setup_logging(level=v)
        return v


settings = Settings()
