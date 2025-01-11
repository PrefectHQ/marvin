"""
Settings for Marvin.
"""

import inspect
from pathlib import Path
from typing import Literal, Optional, Self

from pydantic import Field, field_validator, model_validator
from pydantic_ai.models import KnownModelName
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        extra="forbid",
        validate_assignment=True,
    )

    # ------------ General settings ------------

    home_path: Path = Field(
        default=Path("~/.marvin"),
        description="The home path for Marvin.",
    )

    @field_validator("home_path")
    @classmethod
    def validate_home_path(cls, v: Path) -> Path:
        """Ensure the home path exists."""
        path = Path(v).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    database_path: Optional[Path] = Field(
        default=None,
        description="Path to the database file. Defaults to `home_path / 'marvin.db'`.",
    )

    @model_validator(mode="after")
    def validate_database_path(self) -> Self:
        """Set and validate the database path."""
        # Set default if not provided
        if self.database_path is None:
            self.__dict__["database_path"] = self.home_path / "marvin.db"

        # Convert to Path if string
        self.__dict__["database_path"] = Path(self.database_path)

        # Expand user and resolve to absolute path
        self.__dict__["database_path"] = self.database_path.expanduser().resolve()

        # Ensure parent directory exists
        self.__dict__["database_path"].parent.mkdir(parents=True, exist_ok=True)

        return self

    # ------------ Logging settings ------------

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="DEBUG",
        description="Logging level",
    )

    log_events: bool = Field(
        default=False,
        description="Whether to log all events (as debug logs).",
    )

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

    agent_temperature: Optional[float] = Field(
        default=None,
        description="The temperature for the agent.",
    )

    agent_retries: int = Field(
        default=10,
        description="The number of times the agent is allowed to retry when it generates an invalid result.",
    )

    # ------------ DX settings ------------

    enable_default_print_handler: bool = Field(
        default=True,
        description="Whether to enable the default print handler.",
    )

    # ------------ Memory settings ------------

    memory_provider: str = Field(
        default="chroma-db",
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

    # ------------ Async settings ------------

    apply_nest_asyncio: bool = Field(
        default=True,
        description=inspect.cleandoc("""
            Whether to apply nest_asyncio (default: True). In many cases,
            nest_asyncio makes Marvin's synchronous interface run transparently.
            You can disable it if you're only using async functions, or if
            you're using asyncio in a way that doesn't support nest_asyncio.
            """),
    )


# Global settings instance
settings = Settings()
