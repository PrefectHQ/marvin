import inspect
from datetime import datetime
from enum import Enum
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
    name: str = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    data: dict = {}
    llm_response: dict = Field(None, description="The raw LLM response", repr=False)

    @validator("content")
    def clean_content(cls, v):
        if v is not None:
            v = inspect.cleandoc(v)
        return v
