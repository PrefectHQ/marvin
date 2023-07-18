import datetime

from pydantic import BaseModel, Field, validate_arguments

from marvin.utilities.messages import Message, Role


class HistoryFilter(BaseModel):
    role_in: list[Role] = None
    timestamp_ge: datetime.datetime = None
    timestamp_le: datetime.datetime = None


class History(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    max_messages: int = None

    def add_message(self, message: Message):
        self.messages.append(message)

        if self.max_messages is not None:
            self.messages = self.messages[-self.max_messages :]

    @validate_arguments
    def get_messages(
        self, n: int = None, skip: int = None, filter: HistoryFilter = None
    ) -> list[Message]:
        messages = self.messages.copy()

        if filter is not None:
            if filter.timestamp_ge:
                messages = [m for m in messages if m.timestamp >= filter.timestamp_ge]
            if filter.timestamp_le:
                messages = [m for m in messages if m.timestamp <= filter.timestamp_le]
            if filter.role_in:
                messages = [m for m in messages if m.role in filter.role_in]

        if skip:
            messages = messages[:-skip]

        if n is not None:
            messages = messages[-n:]

        return messages

    def clear(self):
        self.messages.clear()
