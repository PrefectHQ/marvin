import os
from pathlib import Path
from typing import Literal, Optional, Union

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Marvin settings"""

    model_config = SettingsConfigDict(
        env_file=(
            ".env",
            str(Path(os.getenv("MARVIN_ENV_FILE", "~/.marvin/.env")).expanduser()),
        ),
        env_prefix="MARVIN_",
        validate_assignment=True,
        extra="allow",
    )

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
    ai_application_max_iterations: Optional[int] = None

    # OPENAI
    openai_api_key: SecretStr = Field(
        None,
        # validation_alias="MARVIN_OPENAI_API_KEY",
    )
    openai_organization: Optional[str] = Field(None)
    openai_api_base: Optional[str] = Field(None)
    embedding_engine: str = "text-embedding-ada-002"

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

    @field_validator("home")
    def initialize_home(cls, v):
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("log_level")
    def set_log_level(cls, v):
        import marvin.utilities.logging

        marvin.utilities.logging.setup_logging(level=v)
        return v

    @field_validator("openai_api_key")
    def set_openai_api_key(cls, v):
        if v is not None:
            import openai

            openai.api_key = v.get_secret_value()
            return v
        return v


settings = Settings()
