import inspect
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, PrivateAttr
from typing_extensions import Self

from marvin._compat import field_validator
from marvin.utilities.strings import split_text_by_tokens
from marvin.utilities.types import MarvinBaseModel


class Role(Enum):
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"
    FUNCTION_REQUEST = "function"
    FUNCTION_RESPONSE = "function"

    @classmethod
    def _missing_(cls: type[Self], value: object) -> Optional[Self]:
        lower_value = str(value).lower()
        matching_member = next(
            (member for member in cls if member.value.lower() == lower_value), None
        )
        return matching_member


class FunctionCall(BaseModel):
    name: str
    arguments: str


class Message(MarvinBaseModel):
    role: Role
    content: Optional[str] = Field(default=None, description="The message content")

    name: Optional[str] = Field(
        default=None,
        description="The name of the message",
    )

    function_call: Optional[FunctionCall] = Field(default=None)

    # Internal fields for intelligent rendering.
    _timestamp: datetime = PrivateAttr(
        default_factory=lambda: datetime.now(ZoneInfo("UTC"))
    )

    _data: Optional[dict[str, Any]] = PrivateAttr(default_factory=dict)

    _llm_response: Optional[dict[str, Any]] = PrivateAttr(default_factory=dict)

    _id: uuid.UUID = PrivateAttr(default_factory=uuid.uuid4)

    @field_validator("content")
    def clean_content(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = inspect.cleandoc(v)
        return v

    class Config(MarvinBaseModel.Config):
        use_enum_values = True

    @classmethod
    def from_transcript(
        cls: type[Self],
        text: str,
    ) -> list[Self]:
        pairs = split_text_by_tokens(
            text=text, split_tokens=[role.value.capitalize() for role in Role]
        )
        return [
            cls(
                role=Role(pair[0]),
                content=pair[1],
            )
            for pair in pairs
        ]
