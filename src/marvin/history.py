import abc

from pydantic import Field

from marvin.models.threads import Message, MessageCreate
from marvin.utilities.strings import count_tokens
from marvin.utilities.types import DiscriminatingTypeModel


class History(DiscriminatingTypeModel, abc.ABC):
    @abc.abstractmethod
    async def add_message(self, message: MessageCreate):
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


# class ThreadHistory(History):
#     thread_id: ThreadID = Field(default_factory=ThreadID.new)

#     async def add_message(self, message: MessageCreate):
#         await marvin.api.threads.create_message(
#             Message(**message.dict(), thread_id=self.thread_id)
#         )

#     async def _load_messages(self, n: int = None):
#         query = (
#             sa.select(Message)
#             .where(Message.thread_id == self.thread_id)
#             .order_by(Message.timestamp.desc())
#             .limit(n)
#         )

#         async with session_context() as session:
#             result = await session.execute(query)
#             messages = result.scalars().all()

#         return list(messages, key=lambda m: m.timestamp)

#     async def clear(self):
#         self.thread_id = ThreadID.new()


class InMemoryHistory(History):
    messages: list[Message] = Field(default_factory=list)

    async def add_message(self, message: MessageCreate):
        self.messages.append(message)

    async def _load_messages(self, n: int = None) -> list[Message]:
        if n is None:
            return self.messages.copy()
        return self.messages[-n:]

    async def clear(self):
        self.messages.clear()
