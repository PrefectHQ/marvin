from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from pydantic import BaseSettings, Field, SecretStr, root_validator, validator
from rich import print
from rich.text import Text

import marvin


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_prefix = "MARVIN_"
        validate_assignment = True

    home: Path = Path("~/.marvin").expanduser()
    test_mode: bool = False

    # LOGGING
    verbose: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"
    log_console_width: int | None = Field(
        None,
        description=(
            "Marvin will auto-detect the console width when possible, but in deployed"
            " settings logs will assume a console width of 80 characters unless"
            " specified here."
        ),
    )
    rich_tracebacks: bool = Field(False, description="Enable rich traceback formatting")

    # EMBEDDINGS
    # specify the path to the embeddings cache, relative to the home dir
    embeddings_cache_path: Path = Path("cache/embeddings.sqlite")
    embeddings_cache_warn_size: int = 4000000000  # 4GB

    # OPENAI
    openai_api_key: SecretStr = Field(
        "", env=["MARVIN_OPENAI_API_KEY", "OPENAI_API_KEY"]
    )

    # DATABASE
    database_echo: bool = False
    database_connection_url: SecretStr = "sqlite+aiosqlite:////$HOME/marvin.db"

    # REDIS
    redis_connection_url: SecretStr = ""

    # BOTS
    bot_create_profile_picture: bool = False

    @root_validator
    def initial_setup(cls, values):
        values["home"].mkdir(parents=True, exist_ok=True)

        # prefix HOME to embeddings cache path
        if not values["embeddings_cache_path"].is_absolute():
            values["embeddings_cache_path"] = (
                values["home"] / values["embeddings_cache_path"]
            )
        values["embeddings_cache_path"].parent.mkdir(parents=True, exist_ok=True)

        # interpolate HOME into database connection URL
        values["database_connection_url"] = SecretStr(
            values["database_connection_url"]
            .get_secret_value()
            .replace("$HOME", str(values["home"]))
        )

        # print if verbose = True
        if values["verbose"]:
            print(Text("Verbose mode enabled", style="green"))

        return values

    @validator("openai_api_key")
    def warn_if_missing_api_keys(cls, v, field):
        if not v:
            print(
                Text(
                    f"WARNING: `{field.name}` is not set. Some features may not work.",
                    style="red",
                )
            )
        return v

    @root_validator
    def test_mode_settings(cls, values):
        if values["test_mode"]:
            print(Text("Marvin is running in test mode!", style="yellow"))
            values["log_level"] = "DEBUG"
            values["verbose"] = True
        return values

    def __setattr__(self, name, value):
        result = super().__setattr__(name, value)
        # update log level on assignment
        if name == "log_level":
            marvin.utilities.logging.setup_logging()
        return result


settings = Settings()


@contextmanager
def temporary_settings(**kwargs):
    old_settings = settings.dict()
    settings.__dict__.update(kwargs)
    try:
        yield
    finally:
        settings.__dict__.clear()
        settings.__dict__.update(old_settings)
