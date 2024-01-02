from pathlib import Path
from typing import Union

from pydantic import BaseModel, Field, field_validator, model_validator

from marvin.beta.applications.state import State


class DiskState(State):
    path: Path = Field(
        ..., description="The path to the file where state will be stored."
    )

    @field_validator("path")
    def _validate_path(cls, v: Union[str, Path]) -> Path:
        expanded_path = Path(v).expanduser().resolve()
        if not expanded_path.exists():
            expanded_path.parent.mkdir(parents=True, exist_ok=True)
            expanded_path.touch(exist_ok=True)
        return expanded_path

    @model_validator(mode="after")
    def get_state(self) -> "DiskState":
        with open(self.path, "r") as file:
            self.value = file.read() or {}

    def set_state(self, state: Union[BaseModel, dict]):
        super().set_state(state=state)
        with open(self.path, "w") as file:
            file.write(self.render())
