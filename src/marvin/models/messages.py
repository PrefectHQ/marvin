import inspect
from datetime import datetime
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator


class Role(Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    ASSISTANT = "ASSISTANT"
    FUNCTION = "FUNCTION"

    @classmethod
    def _missing_(cls, value):
        value = value.lower()
        for member in cls:
            if member.value.lower() == value:
                return member
        return None


class Message(BaseModel):
    role: Role
    content: Optional[str] = None
    name: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    data: dict = Field(default_factory=dict)

    @field_validator("content")
    def clean_content(cls, v):
        if v is not None:
            v = inspect.cleandoc(v)
        return v

    def as_chat_message(self) -> dict[str, str]:
        msg = {"role": self.role.value.lower(), "content": self.content}
        if self.name:
            msg["name"] = self.name
        return msg

    def as_prompt(self) -> str:
        return f"{self.role}: {self.content}"
