"""Settings for Marvin."""

from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_ai.models import KnownModelName
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


class Settings(BaseSettings):
    """Settings for Marvin.

    Settings can be set via environment variables with the prefix MARVIN_. For
    example, MARVIN_AGENT_MODEL="openai:gpt-4o-mini"
    """

    model_config = SettingsConfigDict(
        env_prefix="MARVIN_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_assignment=True,
    )

    # ------------ General settings ------------

    home_path: Path = Field(
        default=Path("~/.marvin").expanduser(),
        description="The home path for Marvin.",
    )

    @field_validator("home_path")
    @classmethod
    def validate_home_path(cls, v: Path) -> Path:
        """Ensure the home path exists."""
        path = Path(v).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    database_url: str | None = Field(
        default=None,
        description="Database URL. Must be provided with an async-compatible SQLAlchemy dialect. Defaults to `sqlite+aiosqlite:///{{home_path}}/marvin.db`",
    )

    auto_init_sqlite: bool = Field(
        default=True,
        description="""
        For SQLite databases, whether to automatically initialize the database
        on startup if the file doesn't already exist. This is a one-time
        operation to migrate the database to the latest version and will not be
        repeated.""",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str | None, info: ValidationInfo) -> str:
        """Set and validate the database URL."""

        # Set default if not provided
        if v is None:
            home_path = info.data.get("home_path")
            if not home_path:
                raise ValueError("home_path must be set before database_url")
            return f"sqlite+aiosqlite:///{home_path}/marvin.db"

        return v

    # ------------ Logging settings ------------

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    log_file: Path | None = Field(
        default=None,
        description="Path to a file for logging. If None, logs to stdout.",
    )

    log_events: bool = Field(
        default=False,
        description="Whether to log all events (as debug logs).",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        """Validate the log level."""
        return v.upper()

    @model_validator(mode="after")
    def setup_logging(self) -> Self:
        """Finalize the settings."""
        from marvin.utilities.logging import setup_logging

        setup_logging(settings=self)

        return self

    # ------------ Agent settings ------------

    agent_model: KnownModelName = Field(
        default="openai:gpt-4o",
        description="The default model for agents.",
    )

    agent_temperature: float | None = Field(
        default=None,
        description="The temperature for the agent.",
    )

    agent_retries: int = Field(
        default=10,
        description="The number of times the agent is allowed to retry when it generates an invalid result.",
    )

    max_agent_turns: int | None = Field(
        default=100,
        description="The maximum number of turns any agents can take when running orchestrated tasks. Note this is per-invocation.",
    )

    # ------------ DX settings ------------

    enable_default_print_handler: bool = Field(
        default=True,
        description="Whether to enable the default print handler.",
    )

    default_print_handler_hide_end_turn_tools: bool = Field(
        default=False,
        description="Whether to hide end turn tool results in the default print handler.",
    )

    # ------------ Memory settings ------------

    memory_provider: str = Field(
        default="chroma-ephemeral",
        description="The default memory provider for agents.",
    )

    chroma_cloud_api_key: str | None = Field(
        default=None,
        description="The API key for the Chroma Cloud.",
    )

    chroma_cloud_tenant: str | None = Field(
        default=None,
        description="The tenant for the Chroma Cloud.",
    )

    chroma_cloud_database: str | None = Field(
        default=None,
        description="The database for the Chroma Cloud.",
    )


# Global settings instance
settings = Settings()
