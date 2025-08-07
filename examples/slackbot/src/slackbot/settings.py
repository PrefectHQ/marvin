from pathlib import Path
from typing import ClassVar, Literal

from prefect.variables import Variable
from pydantic import Field, field_validator, model_validator
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

    temperature: float = Field(
        default=0.2, description="Temperature for model inference"
    )
    user_message_max_tokens: int = Field(
        default=500, description="Maximum tokens allowed in user messages"
    )

    github_token_secret_name: str = Field(
        default="marvin-slackbot-github-token",
        description="Name of the Prefect secret block containing GitHub API token",
    )
    claude_key_secret_name: str = Field(
        default="claude-api-key",
        description="Name of the Prefect secret block containing Claude API key",
    )
    openai_api_key_secret_name: str = Field(
        default="openai-api-key",
        description="Name of the Prefect secret block containing OpenAI API key",
    )
    anthropic_key_secret_name: str = Field(
        default="anthropic-api-key",
        description="Name of the Prefect secret block containing Anthropic API key",
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

    slack_api_token: str = Field(default=..., description="Slack API bot user token")

    @model_validator(mode="after")
    def validate_temperature(self) -> "SlackbotSettings":
        if "gpt-5" in self.model_name:
            self.temperature = 1.0
        return self

    @property
    def model_name(self) -> str:
        return Variable.get(
            "marvin_ai_model",
            default="claude-3-5-sonnet-latest",
            _sync=True,  # type: ignore
        )


settings = SlackbotSettings()
