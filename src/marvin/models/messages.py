from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from marvin.utilities.strings import jinja_env


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

    def as_chat_message(self) -> dict[str, str]:
        msg = {"role": self.role.value.lower(), "content": self.content}
        if self.name:
            msg["name"] = self.name
        return msg

    def as_prompt(self) -> str:
        return f"{self.role}: {self.content}"

    def render(self, **kwargs) -> "Message":
        return Message(
            content=jinja_env.from_string(self.content).render(**kwargs),
            **self.dict(exclude={"content"}),
        )
