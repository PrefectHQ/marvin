import inspect
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, validator


class Role(Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    ASSISTANT = "ASSISTANT"
    FUNCTION = "FUNCTION"


class Message(BaseModel):
    role: Role
    content: str = None
    name: str = None
    position: float = 1
    timestamp: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    data: dict = {}

    @validator("content")
    def clean_content(cls, v):
        v = inspect.cleandoc(v)
        return v

    def as_chat_message(self) -> dict[str, str]:
        msg = {"role": self.role.value.lower(), "content": self.content}
        if self.name:
            msg["name"] = self.name
        return msg

    def as_prompt(self) -> str:
        return f"{self.role}: {self.content}"
