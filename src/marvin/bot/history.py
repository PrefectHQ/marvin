import abc

from pydantic import Field

import marvin
from marvin.models.ids import ThreadID
from marvin.models.threads import Message, MessageCreate
from marvin.utilities.strings import count_tokens
from marvin.utilities.types import DiscriminatedUnionType


class History(DiscriminatedUnionType, abc.ABC):
    @abc.abstractmethod
    async def add_message(self, message: Message):
        raise NotImplementedError()

    @abc.abstractmethod
    async def _load_messages(self, n: int = None) -> list[Message]:
        raise NotImplementedError()

    async def get_messages(
        self, n: int = None, max_tokens: int = None
    ) -> list[Message]:
        messages = await self._load_messages(n=n)

        # sort in reverse timestamp order
        messages = sorted(messages, key=lambda m: m.timestamp, reverse=True)

        if max_tokens is None:
            final_messages = messages
        else:
            total_tokens = 0
            final_messages = []
            for msg in messages:
                msg_tokens = count_tokens(msg.content)
                if total_tokens + msg_tokens > max_tokens:
                    break
                else:
                    final_messages.append(msg)
                    total_tokens += msg_tokens

        return list(reversed(final_messages))

    @abc.abstractmethod
    async def clear(self):
        raise NotImplementedError()


class ThreadHistory(History):
    thread_id: ThreadID = Field(default_factory=ThreadID.new)

    async def add_message(self, message: MessageCreate):
        await marvin.api.threads.create_message(
            message=message, thread_id=self.thread_id
        )

    async def _load_messages(self, n: int = None):
        return await marvin.api.threads.get_messages(thread_id=self.thread_id, limit=n)

    async def clear(self):
        self.thread_id = ThreadID.new()

    async def log(self):
        return (
            "\n\n".join(
                [
                    f"**{m.role}**: {m.content} [{m.timestamp}]"
                    for m in await self._load_messages()
                ]
            )
            or "No Recorded History"
        )


class InMemoryHistory(History):
    messages: list[Message] = Field(default_factory=list)
    max_messages: int = Field(
        None,
        description=(
            "The maximum number of messages to store. Set to 1 to only store the most"
            " recent message. Set to None to store all messages."
        ),
    )

    async def add_message(self, message: Message):
        self.messages.append(message)
        if self.max_messages is not None:
            self.messages = self.messages[-self.max_messages :]

    async def _load_messages(self, n: int = None) -> list[Message]:
        if n is None:
            return self.messages.copy()
        return self.messages[-n:]

    async def clear(self):
        self.messages.clear()
