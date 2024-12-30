"""
Settings for Marvin.
"""

from pathlib import Path
from typing import Literal, Union

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for Marvin.

    Settings can be set via environment variables with the prefix MARVIN_.
    For example, MARVIN_DEFAULT_MODEL="gpt-4"
    """

    model_config = SettingsConfigDict(
        env_prefix="MARVIN_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    database_path: Path = Field(
        default="~/.marvin/marvin.db",
        description="Path to the database file",
    )

    # Logging settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # LLM settings
    agent_model: str = Field(
        default="openai:gpt-4o",
        description="The default model for agents.",
    )

    agent_retries: int = Field(
        default=10,
        description="The number of times the agent is allowed to retry when it generates an invalid result.",
    )

    enable_default_print_handler: bool = Field(
        default=True,
        description="Whether to enable the default print handler.",
    )

    @field_validator("database_path")
    def validate_database_path(cls, v: Union[str, Path]) -> Path:
        """Validate and normalize the database path."""
        # Convert to Path if string
        path = Path(v)

        # Expand user and resolve to absolute path
        path = path.expanduser().resolve()

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        return path

    @model_validator(mode="after")
    def finalize(self) -> None:
        """Finalize the settings."""
        import marvin.utilities.logging

        marvin.utilities.logging.setup_logging(self.log_level)

        return self


# Global settings instance
settings = Settings()
