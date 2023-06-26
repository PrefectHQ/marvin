from pydantic import BaseModel, Field

from marvin.models.messages import Message


class History(BaseModel):
    messages: list[Message] = Field(default_factory=list)

    def add_message(self, message: Message):
        self.messages.append(message)

    def get_messages(self, n: int = None) -> list[Message]:
        if n is None:
            return self.messages.copy()
        return self.messages[-n:]

    def clear(self):
        self.messages.clear()
