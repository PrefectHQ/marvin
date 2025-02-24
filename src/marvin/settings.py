"""Settings for Marvin."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

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
        description="Database URL. Defaults to `sqlite+aiosqlite://{{home_path}}/marvin.db`.",
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

        # Handle in-memory database
        if v == ":memory:":
            return "sqlite+aiosqlite:///:memory:"

        # Parse the URL to handle different database types
        parsed = urlparse(v)

        # Ensure URL has a dialect
        if not parsed.scheme:
            raise ValueError(
                "Database URL must include a dialect prefix (e.g., 'sqlite+aiosqlite://')"
            )

        # For SQLite, ensure the parent directory exists
        if parsed.scheme.startswith("sqlite"):
            # Handle the special case where path might be relative
            if parsed.netloc:
                # URL format: sqlite:///path/to/db
                db_path = Path(parsed.netloc + parsed.path)
            else:
                # URL format: sqlite:/path/to/db
                db_path = Path(parsed.path)

            # Expand user and resolve path
            db_path = db_path.expanduser().resolve()
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Reconstruct the URL with the resolved path
            return f"sqlite+aiosqlite:///{db_path}"

        return v

    # ------------ Logging settings ------------

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
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
        import marvin.utilities.logging

        marvin.utilities.logging.setup_logging(self.log_level)

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
