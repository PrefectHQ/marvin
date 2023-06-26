from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field


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

    def as_openai_chat_message(self) -> dict[str, str]:
        return {
            "role": self.role.value.lower(),
            "content": self.content,
            "name": self.name,
        }

    def as_openai_prompt(self) -> str:
        return f"{self.role}: {self.content}"
