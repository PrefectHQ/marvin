import abc

import sqlalchemy as sa
from pydantic import Field

import marvin
from marvin.infra.db import session_context
from marvin.models.ids import ThreadID
from marvin.models.messages import Message, MessageCreate
from marvin.utilities.types import TaggedModel


class History(TaggedModel, abc.ABC):
    @abc.abstractmethod
    async def add_message(self, message: MessageCreate):
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_messages(self, n: int = None) -> list[Message]:
        raise NotImplementedError()

    @abc.abstractmethod
    async def clear(self):
        raise NotImplementedError()


class ThreadHistory(History):
    thread_id: ThreadID = Field(default_factory=ThreadID.new)

    async def add_message(self, message: MessageCreate):
        await marvin.api.threads.create_message(
            Message(**message.dict(), thread_id=self.thread_id)
        )

    async def get_messages(self, n: int = None):
        query = (
            sa.select(Message)
            .where(Message.thread_id == self.thread_id)
            .order_by(Message.timestamp.desc())
            .limit(n)
        )

        async with session_context() as session:
            result = await session.execute(query)
            messages = result.scalars().all()

        return list(sorted(messages, key=lambda m: m.timestamp))

    async def clear(self):
        self.thread_id = ThreadID.new()


class InMemoryHistory(History):
    messages: list[Message] = Field(default_factory=list)

    async def add_message(self, message: MessageCreate):
        self.messages.append(message)

    async def get_messages(self, n: int = None) -> list[Message]:
        if n is None:
            return self.messages.copy()
        return self.messages[-n:]

    async def clear(self):
        self.messages.clear()
