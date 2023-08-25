import inspect
from datetime import datetime
from enum import Enum
from typing import Optional, Self, Type
from zoneinfo import ZoneInfo

from pydantic import Field, validator

from marvin.utilities.types import MarvinBaseModel


class Role(Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    ASSISTANT = "ASSISTANT"
    FUNCTION_REQUEST = "FUNCTION_REQUEST"
    FUNCTION_RESPONSE = "FUNCTION_RESPONSE"

    @classmethod
    def _missing_(cls, value):
        value = value.lower()
        for member in cls:
            if member.value.lower() == value:
                return member
        return None


class Message(MarvinBaseModel):
    role: Role
    content: str = None
    name: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    data: dict = {}
    llm_response: dict = Field(None, description="The raw LLM response", repr=False)

    @validator("content")
    def clean_content(cls, v):
        if v is not None:
            v = inspect.cleandoc(v)
        return v

    def dict(self, *args, serialize: bool = True, **kwargs):
        if serialize:
            d = super().dict(
                *args, **kwargs, exclude={"llm_response", "data", "timestamp"}
            )
            if isinstance(self.role, Role):
                d["role"] = self.role.value.lower()
            if "name" in d and d["name"] is None:
                del d["name"]

            return d
        return super().dict(*args, **kwargs)

    @classmethod
    def from_conversation(cls: Type[Self], conversation) -> list[Type[Self]]:
        messages = []
        for turn in conversation.turns:
            choice = turn.raw.get("choices", [{}])[0]
            created_at = datetime.fromtimestamp(turn.raw.get("created"))
            message_data = choice.get("message", {})
            role = message_data.get("role")
            content = message_data.get("content")

            message = cls(
                role=role,
                content=content,
                name=message_data.get("name"),
                timestamp=created_at,
                data=turn.raw,
            )
            messages.append(message)

        return messages
