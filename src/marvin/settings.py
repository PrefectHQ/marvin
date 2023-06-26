import os
from pathlib import Path
from typing import Literal, Union

from pydantic import BaseSettings, Field, SecretStr, root_validator, validator


class Settings(BaseSettings):
    """Marvin settings"""

    class Config:
        env_file = (
            ".env",
            str(Path(os.getenv("MARVIN_ENV_FILE", "~/.marvin/.env")).expanduser()),
        )
        env_prefix = "MARVIN_"
        validate_assignment = True

    home: Path = Path("~/.marvin").expanduser()
    test_mode: bool = False

    # LOGGING
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    verbose: bool = False

    # LLMS
    llm_model: str = "gpt-3.5-turbo-0613"
    llm_max_tokens: int = 1500
    llm_temperature: float = 0.8
    llm_request_timeout_seconds: Union[float, list[float]] = 600.0

    # OPENAI
    openai_api_key: SecretStr = Field(
        None,
        # for OpenAI convenience, we first check the Marvin-specific env var,
        # then the generic one
        env=["MARVIN_OPENAI_API_KEY", "OPENAI_API_KEY"],
    )
    openai_organization: str = Field(None)
    openai_api_base: str = None

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
