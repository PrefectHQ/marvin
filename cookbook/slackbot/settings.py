import os
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SlackbotSettings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="MARVIN_SLACKBOT_", env_file=".env", extra="allow"
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Host to run the server on")
    port: int = Field(default=4200, description="Port to run the server on")

    # Logging settings
    log_level: str = Field(default="INFO")
    log_format: str = Field(
        default="\x1b[32m%(asctime)s\x1b[0m \x1b[34m%(name)-12s\x1b[0m %(levelname)-8s %(message)s",
    )
    log_date_format: str = Field(default="%Y-%m-%d %H:%M:%S")

    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        return v.upper()

    # Existing settings...
    db_file: Path = Field(
        default=Path("marvin_chat.sqlite"), description="Path to SQLite database file"
    )

    model_name: str = Field(
        default="claude-3-5-sonnet-latest", description="Name of the AI model to use"
    )
    temperature: float = Field(
        default=0.5, description="Temperature for model inference"
    )
    user_message_max_tokens: int = Field(
        default=300, description="Maximum tokens allowed in user messages"
    )

    github_token_secret_name: str = Field(
        default="marvin-slackbot-github-token",
        description="Name of the Prefect secret block containing GitHub API token",
    )
    claude_key_secret_name: str = Field(
        default="claude-api-key",
        description="Name of the Prefect secret block containing Claude API key",
    )

    vector_store_type: Literal["turbopuffer"] = Field(
        default="turbopuffer", description="Type of vector store to use"
    )
    user_facts_namespace_prefix: str = Field(
        default="user-facts-",
        description="Prefix for user facts namespaces in vector store",
    )

    # Development settings
    test_mode: bool = Field(
        default=False, description="Enable test mode with auto-reload"
    )

    @property
    def slack_api_token(self) -> str:
        from prefect.blocks.system import Secret

        if self.test_mode:
            return Secret.load("test-slack-api-token", _sync=True).get()  # type: ignore
        else:
            token = os.getenv("MARVIN_SLACK_API_TOKEN")
            assert token is not None, "MARVIN_SLACK_API_TOKEN is not set"
            return token


settings = SlackbotSettings()
