import inspect
from datetime import datetime
from enum import Enum
from typing import Optional, Self, Type
from zoneinfo import ZoneInfo

from pydantic import Field, validator

from marvin.core.conversations import Conversation
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

    @classmethod
    def from_conversation(
        cls: Type[Self], conversation: Conversation
    ) -> list[Type[Self]]:
        messages = []
        for turn in conversation.turns:
            message = turn.response.message

            message = cls(
                role=message.role,
                content=message.content,
                name=message.name,
            )
            messages.append(message)

        return messages
