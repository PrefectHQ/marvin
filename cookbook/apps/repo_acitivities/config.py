from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def ensure_home_path(home_path: Path) -> Path:
    home_path.mkdir(parents=True, exist_ok=True)
    return home_path


HomePath = Annotated[Path, AfterValidator(ensure_home_path)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="REPO_ACTIVITIES_",
        extra="ignore",
    )

    home: HomePath = Field(default_factory=lambda: Path.home() / ".repo_activities")

    test_mode: bool = False


settings = Settings()
