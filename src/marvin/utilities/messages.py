"""
Message Role and Model for Marvin Framework
===========================================

This module provides enumerations and data models that represent various message roles
and the structure of a message within the Marvin framework.

- The `Role` enumeration defines various roles that a message can have.
- The `Message` model provides the structure of a message, including its role, 
  content, name, timestamp, and associated data.
"""

import inspect
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from zoneinfo import ZoneInfo

from pydantic import Field

from marvin._compat import field_validator
from marvin.utilities.types import MarvinBaseModel


class Role(Enum):
    """
    Enumeration representing the roles of a message.

    The Role can be one of the following:
    - USER: Represents a user's message.
    - SYSTEM: Represents a system-generated message.
    - ASSISTANT: Represents a message from an assistant.
    - FUNCTION_REQUEST: Represents a request to a function.
    - FUNCTION_RESPONSE: Represents a response from a function.
    """

    USER = "USER"
    SYSTEM = "SYSTEM"
    ASSISTANT = "ASSISTANT"
    FUNCTION_REQUEST = "FUNCTION_REQUEST"
    FUNCTION_RESPONSE = "FUNCTION_RESPONSE"

    @classmethod
    def _missing_(cls, value: object) -> Optional["Role"]:
        """
        Handle case-insensitive enum value retrieval.

        Args:
        - value (str): The value to search for.

        Returns:
        - Role: The matched Role enum member or None.
        """
        value = str(value).lower()
        for member in cls:
            if member.value.lower() == value:
                return member


class Message(MarvinBaseModel):
    """
    Model representing a message within the Marvin framework.

    Attributes:
    - role (Role): The role of the message.
    - content (str, optional): The main content of the message.
    - name (str, optional): The name associated with the message.
    - timestamp (datetime): The time the message was created.
    - data (dict): Any additional data associated with the message.
    - llm_response (dict, optional): The raw LLM response.
                                     It won't appear in object representations.
    """

    role: Role
    content: Optional[str] = None
    name: Optional[str] = None

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(ZoneInfo("UTC")), repr=False
    )
    data: dict[str, Any] = Field(default_factory=dict, repr=False)
    llm_response: Optional[dict[str, Any]] = Field(
        default=None, description="The raw LLM response", repr=False
    )

    @field_validator("content")
    def clean_content(cls, content: Optional[str]) -> Optional[str]:
        """
        Cleans the content of the message by removing leading indentation.

        Args:
        - content (str): The original content.

        Returns:
        - str: The cleaned content.
        """
        return inspect.cleandoc(content) if content is not None else None
