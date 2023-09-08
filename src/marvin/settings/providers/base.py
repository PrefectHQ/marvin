import os
from pathlib import Path
from typing import ClassVar

from ..._compat import BaseSettings

env_path = Path(os.getenv("MARVIN_ENV_FILE", "~/.marvin/.env")).expanduser()


class MarvinBaseSettings(BaseSettings):  # type: ignore
    home: ClassVar[Path] = env_path

    class Config:
        env_file = (".env", str(env_path))
        env_prefix = "MARVIN_"
        validate_assignment = True
