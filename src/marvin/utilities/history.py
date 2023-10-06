import datetime
from typing import Optional

from pydantic import Field

from marvin._compat import BaseModel
from marvin.utilities.messages import Message, Role


class HistoryFilter(BaseModel):
    role_in: list[Role] = Field(default_factory=list)
    timestamp_ge: Optional[datetime.datetime] = None
    timestamp_le: Optional[datetime.datetime] = None


class History(BaseModel, arbitrary_types_allowed=True):
    messages: list[Message] = Field(default_factory=list)
    max_messages: int = None

    def add_message(self, message: Message):
        if not any(
            existing_message._id == message._id for existing_message in self.messages
        ):
            self.messages.append(message)

            if self.max_messages is not None:
                self.messages = self.messages[-self.max_messages :]

    def get_messages(
        self, n: int = None, skip: int = None, filter: HistoryFilter = None
    ) -> list[Message]:
        messages = self.messages.copy()

        if filter is not None:
            if filter.timestamp_ge:
                messages = [m for m in messages if m._timestamp >= filter.timestamp_ge]
            if filter.timestamp_le:
                messages = [m for m in messages if m._timestamp <= filter.timestamp_le]
            if filter.role_in:
                messages = [m for m in messages if m.role in filter.role_in]

        if skip:
            messages = messages[:-skip]

        if n is not None:
            messages = messages[-n:]

        return messages

    def clear(self):
        self.messages.clear()
