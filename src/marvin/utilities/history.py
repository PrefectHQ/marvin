"""
History Models and Utilities for Marvin Framework
=================================================

This module provides data models and utilities to handle and filter message history 
within the Marvin framework.

Classes:
- HistoryFilter: Provides filtering capabilities on message history based on roles and timestamps.
- History: Represents the history of messages with functionalities to add, retrieve, and clear messages.
"""  # noqa: E501

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from marvin.utilities.messages import Message, Role


class HistoryFilter(BaseModel):
    """
    Provides filtering capabilities on message history.

    Attributes:
    - role_in (Optional[List[Role]]): Filter messages based on their roles.
    - timestamp_ge (Optional[datetime]): Filter messages after or equal to this timestamp.
    - timestamp_le (Optional[datetime]): Filter messages before or equal to this timestamp.
    """  # noqa: E501

    role_in: Optional[List[Role]] = None
    timestamp_ge: Optional[datetime] = None
    timestamp_le: Optional[datetime] = None


class History(BaseModel):
    """
    Represents the history of messages.

    Attributes:
    - messages (List[Message]): List of messages in the history.
    - max_messages (Optional[int]): Maximum number of messages to retain in the history.
    """

    messages: List[Message] = Field(default_factory=list)
    max_messages: Optional[int] = None

    def add_message(self, message: Message) -> None:
        """
        Add a message to the history.

        If max_messages is set, it ensures that only the last 'max_messages'
        are retained in the history.

        Args:
        - message (Message): The message to add.
        """
        self.messages.append(message)
        if self.max_messages is not None:
            self.messages = self.messages[-self.max_messages :]

    def get_messages(
        self,
        n: Optional[int] = None,
        skip: Optional[int] = None,
        filter: Optional[HistoryFilter] = None,
    ) -> List[Message]:
        """
        Retrieve messages from the history based on the provided filters.

        Args:
        - n (Optional[int]): Number of messages to retrieve.
        - skip (Optional[int]): Number of messages to skip from the end.
        - filter (Optional[HistoryFilter]): Filtering criteria.

        Returns:
        - List[Message]: List of filtered messages.
        """
        messages = self.messages.copy()

        if filter:
            if filter.timestamp_ge:
                messages = [m for m in messages if m.timestamp >= filter.timestamp_ge]
            if filter.timestamp_le:
                messages = [m for m in messages if m.timestamp <= filter.timestamp_le]
            if filter.role_in:
                messages = [m for m in messages if m.role in filter.role_in]

        if skip:
            messages = messages[:-skip]
        if n:
            messages = messages[-n:]

        return messages

    def clear(self) -> None:
        """Clear all messages from the history."""
        self.messages.clear()
