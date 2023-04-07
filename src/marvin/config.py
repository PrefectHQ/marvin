import os
import platform
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, Optional

try:
    import chromadb

    CHROMA_INSTALLED = True
except ModuleNotFoundError:
    CHROMA_INSTALLED = False


if platform.system() == "Windows":
    DEFAULT_DB_CONNECTION_URL = "sqlite+aiosqlite:///$MARVIN_HOME/marvin.sqlite"
else:
    DEFAULT_DB_CONNECTION_URL = "sqlite+aiosqlite:////$MARVIN_HOME/marvin.sqlite"

from pydantic import BaseSettings, Field, SecretStr, root_validator, validator
from rich import print
from rich.text import Text

import marvin

# a configurable env file location
ENV_FILE = Path(os.getenv("MARVIN_ENV_FILE", "~/.marvin/.env")).expanduser()
ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
ENV_FILE.touch(exist_ok=True)

if CHROMA_INSTALLED:

    class ChromaSettings(chromadb.config.Settings):
        class Config:
            env_file = ".env", str(ENV_FILE)
            env_prefix = "MARVIN_CHROMA_"

        chroma_db_impl: Literal["duckdb", "duckdb+parquet"] = "duckdb+parquet"

        # relative paths will be prefixed with the marvin home directory
        persist_directory: str = "chroma"

else:

    class ChromaSettings(BaseSettings):
        pass


class Settings(BaseSettings):
    """Marvin settings"""

    class Config:
        env_file = ".env", str(ENV_FILE)
        env_prefix = "MARVIN_"
        validate_assignment = True

    def export_to_env_file(self):
        with open(self.Config.env_file, "w") as env_file:
            for field_name, value in self.dict().items():
                env_key = f"{self.Config.env_prefix}{field_name.upper()}"
                env_value = (
                    str(value)
                    if not isinstance(value, SecretStr)
                    else value.get_secret_value()
                )
                env_file.write(f"{env_key}={env_value}\n")

    home: Path = Path("~/.marvin").expanduser()
    test_mode: bool = False

    # LOGGING
    verbose: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_console_width: Optional[int] = Field(
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
    openai_model_name: str = "gpt-3.5-turbo"
    openai_model_temperature: float = 0.8
    openai_model_max_tokens: int = 1250
    openai_api_key: SecretStr = Field(
        "", env=["MARVIN_OPENAI_API_KEY", "OPENAI_API_KEY"]
    )

    # CHROMA
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)

    # DISCOURSE
    DISCOURSE_API_KEY: SecretStr = Field(
        "", env=["MARVIN_DISCOURSE_API_KEY", "DISCOURSE_API_KEY"]
    )
    DISCOURSE_API_USERNAME: str = Field(
        "nate", env=["MARVIN_DISCOURSE_API_USERNAME", "DISCOURSE_API_USERNAME"]
    )

    # DOCUMENTS
    default_topic = "marvin"
    default_n_keywords: int = 15

    # DATABASE
    database_echo: bool = False
    database_connection_url: SecretStr = DEFAULT_DB_CONNECTION_URL
    database_check_migration_version_on_startup: bool = True

    # GITHUB
    GITHUB_TOKEN: SecretStr = Field("", env=["MARVIN_GITHUB_TOKEN", "GITHUB_TOKEN"])

    # REDIS
    redis_connection_url: SecretStr = ""

    # BOTS
    bot_create_profile_picture: bool = Field(
        True,
        description=(
            "if True, a profile picture will be generated for new bots when they are"
            " saved in the database."
        ),
    )
    bot_max_iterations: int = 10
    bot_load_default_plugins: bool = Field(
        True,
        description=(
            "If True, bots will load a default set of plugins if none are provided."
        ),
    )

    # API
    api_base_url: str = "http://127.0.0.1"
    api_port: int = 4200
    api_reload: bool = Field(
        False,
        description=(
            "If true, the API will reload on file changes. Use only for development."
        ),
    )

    @root_validator
    def initial_setup(cls, values):
        values["home"].mkdir(parents=True, exist_ok=True)

        # prefix HOME to embeddings cache path
        if not values["embeddings_cache_path"].is_absolute():
            values["embeddings_cache_path"] = (
                values["home"] / values["embeddings_cache_path"]
            )
        values["embeddings_cache_path"].parent.mkdir(parents=True, exist_ok=True)

        if CHROMA_INSTALLED:
            # prefix HOME to chroma path
            chroma_persist_directory = Path(values["chroma"]["persist_directory"])
            if not chroma_persist_directory.is_absolute():
                chroma_persist_directory = values["home"] / chroma_persist_directory
                values["chroma"] = ChromaSettings(
                    **values["chroma"].dict(exclude={"persist_directory"}),
                    persist_directory=str(chroma_persist_directory),
                )

        # interpolate HOME into database connection URL
        values["database_connection_url"] = SecretStr(
            values["database_connection_url"]
            .get_secret_value()
            .replace("$MARVIN_HOME", str(values["home"]))
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
            values["log_level"] = "DEBUG"
            values["verbose"] = True
            # don't generate profile pictures
            values["bot_create_profile_picture"] = False
            # don't load default plugins
            values["bot_load_default_plugins"] = False
            # remove all model variance
            values["openai_model_temperature"] = 0.0
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
