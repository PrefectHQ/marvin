"""
Settings for Marvin.
"""

from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, field_validator, model_validator
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
    )

    # ------------ General settings ------------

    home_path: Path = Field(
        default="~/.marvin",
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
    def validate_database_path(self) -> "Settings":
        """Set and validate the database path."""
        # Set default if not provided
        if self.database_path is None:
            self.database_path = self.home_path / "marvin.db"

        # Convert to Path if string
        self.database_path = Path(self.database_path)

        # Expand user and resolve to absolute path
        self.database_path = self.database_path.expanduser().resolve()

        # Ensure parent directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        return self

    # ------------ Logging settings ------------

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    @model_validator(mode="after")
    def finalize(self) -> None:
        """Finalize the settings."""
        import marvin.utilities.logging

        marvin.utilities.logging.setup_logging(self.log_level)

        return self

    # ------------ Agent settings ------------

    agent_model: str = Field(
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


# Global settings instance
settings = Settings()
