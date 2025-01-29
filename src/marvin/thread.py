"""Thread management for conversations.

This module provides the Thread class for managing conversation context.
"""

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from pydantic import TypeAdapter
from pydantic_ai.usage import Usage
from sqlalchemy import select

from marvin.database import DBLLMCall, DBMessage, DBThread, get_async_session
from marvin.utilities.asyncio import run_sync

from .engine.llm import Message, UserMessage

# Message serialization adapter
message_adapter: TypeAdapter[Message | list[Message]] = TypeAdapter(
    Message | list[Message]
)


@dataclass
class LLMCall:
    """Represents an LLM call."""

    id: uuid.UUID
    thread_id: str
    usage: Usage
    timestamp: datetime

    @classmethod
    def from_db(cls, db_call: DBLLMCall) -> "LLMCall":
        """Create an LLMCall from a database record."""
        return cls(
            id=db_call.id,
            thread_id=db_call.thread_id,
            usage=db_call.usage,
            timestamp=db_call.timestamp,
        )


# Global context var for current thread
_current_thread: ContextVar[Optional["Thread"]] = ContextVar(
    "current_thread",
    default=None,
)

# Track the last thread globally
_last_thread: Optional["Thread"] = None


@dataclass
class Thread:
    """Main runtime object for managing conversation context."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    _db_thread: DBThread | None = field(default=None, init=False, repr=False)
    _tokens: list[Any] = field(default_factory=list, init=False, repr=False)

    async def _ensure_thread_exists(self) -> None:
        """Ensure thread exists in database."""
        if self._db_thread is not None:
            return

        async with get_async_session() as session:
            self._db_thread = await session.get(DBThread, self.id)
            if not self._db_thread:
                self._db_thread = await DBThread.create(
                    session=session,
                    id=self.id,
                    parent_thread_id=self.parent_id,
                )

    def add_messages(
        self, messages: list[Message], llm_call_id: uuid.UUID | None = None
    ):
        """Add multiple messages to the thread.

        Args:
            messages: List of messages to add (UserMessage, AssistantMessage, etc.)
            llm_call_id: Optional ID of the LLM call that generated these messages

        """
        return run_sync(self.add_messages_async(messages, llm_call_id=llm_call_id))

    async def add_messages_async(
        self, messages: list[Message], llm_call_id: uuid.UUID | None = None
    ):
        """Add multiple messages to the thread.

        Args:
            messages: List of messages to add (UserMessage, AssistantMessage, etc.)
            llm_call_id: Optional ID of the LLM call that generated these messages

        """
        await self._ensure_thread_exists()

        async with get_async_session() as session:
            for message in messages:
                db_message = DBMessage.from_message(
                    thread_id=self.id,
                    message=message,
                    llm_call_id=llm_call_id,
                )
                session.add(db_message)
            await session.commit()

    def add_user_message(self, message: str):
        """Add a user message to the thread."""
        return run_sync(self.add_user_message_async(message))

    async def add_user_message_async(self, message: str) -> None:
        """Add a user message to the thread."""
        await self.add_messages_async([UserMessage(content=message)])

    def get_messages(
        self,
        before: datetime | None = None,
        after: datetime | None = None,
        limit: int | None = None,
    ) -> list[Message]:
        """Get all messages in this thread.

        Args:
            before: Only return messages before this timestamp
            after: Only return messages after this timestamp
            limit: Maximum number of messages to return

        Returns:
            List of messages in chronological order
        """
        return run_sync(
            self.get_messages_async(
                before=before,
                after=after,
                limit=limit,
            ),
        )

    async def get_messages_async(
        self,
        before: datetime | None = None,
        after: datetime | None = None,
        limit: int | None = None,
    ) -> list[Message]:
        """Get all messages in this thread.

        Args:
            before: Only return messages before this timestamp
            after: Only return messages after this timestamp
            limit: Maximum number of messages to return

        Returns:
            List of messages in chronological order
        """
        await self._ensure_thread_exists()

        async with get_async_session() as session:
            query = select(DBMessage).where(DBMessage.thread_id == self.id)

            if before is not None:
                query = query.where(DBMessage.timestamp < before)
            if after is not None:
                query = query.where(DBMessage.timestamp > after)

            query = query.order_by(DBMessage.timestamp)

            if limit is not None:
                query = query.limit(limit)

            result = await session.execute(query)

            return message_adapter.validate_python(
                [m.message for m in result.scalars().all()]
            )

    async def get_llm_calls_async(
        self,
        before: datetime | None = None,
        after: datetime | None = None,
        limit: int | None = None,
    ) -> list[LLMCall]:
        """Get LLM calls for this thread.

        Args:
            before: Only return calls before this timestamp
            after: Only return calls after this timestamp
            limit: Maximum number of calls to return

        Returns:
            List of LLM calls in chronological order
        """
        await self._ensure_thread_exists()

        async with get_async_session() as session:
            query = select(DBLLMCall).where(DBLLMCall.thread_id == self.id)

            if before is not None:
                query = query.where(DBLLMCall.timestamp < before)
            if after is not None:
                query = query.where(DBLLMCall.timestamp > after)

            query = query.order_by(DBLLMCall.timestamp)

            if limit is not None:
                query = query.limit(limit)

            result = await session.execute(query)
            return [LLMCall.from_db(call) for call in result.scalars().all()]

    def get_llm_calls(
        self,
        before: datetime | None = None,
        after: datetime | None = None,
        limit: int | None = None,
    ) -> list[LLMCall]:
        """Get LLM calls for this thread.

        Args:
            before: Only return calls before this timestamp
            after: Only return calls after this timestamp
            limit: Maximum number of calls to return

        Returns:
            List of LLM calls in chronological order
        """
        return run_sync(
            self.get_llm_calls_async(before=before, after=after, limit=limit)
        )

    async def get_usage_async(
        self,
        before: datetime | None = None,
        after: datetime | None = None,
    ) -> Usage:
        """Get the usage for this thread.

        Args:
            before: Only include usage before this timestamp
            after: Only include usage after this timestamp

        Returns:
            Total usage for the specified time range
        """
        await self._ensure_thread_exists()

        usage = Usage()

        llm_calls = await self.get_llm_calls_async(before=before, after=after)
        for llm_call in llm_calls:
            usage.incr(llm_call.usage)

        return usage

    def get_usage(
        self,
        before: datetime | None = None,
        after: datetime | None = None,
    ) -> Usage:
        """Get the usage for this thread.

        Args:
            before: Only include usage before this timestamp
            after: Only include usage after this timestamp

        Returns:
            Total usage for the specified time range
        """
        return run_sync(self.get_usage_async(before=before, after=after))

    def __enter__(self):
        """Set this thread as the current thread in context."""
        token = _current_thread.set(self)
        self._tokens.append(token)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        """Reset the current thread in context and store it as the last thread."""
        global _last_thread
        # Store this thread as the last thread before resetting current
        _last_thread = self
        if self._tokens:  # Only reset if we have tokens
            _current_thread.reset(self._tokens.pop())

    @classmethod
    def get_current(cls) -> Optional["Thread"]:
        """Get the current thread from context."""
        return _current_thread.get()


def get_current_thread() -> Thread | None:
    """Get the currently active thread from context.

    Returns:
        The current Thread instance or None if no thread is active.

    """
    return Thread.get_current()


def get_last_thread() -> Thread | None:
    """Get the last thread that was set as current.

    This function is for debugging purposes only, and will only work in certain
    contexts.
    """
    return _last_thread


def get_thread(thread: Thread | str | None) -> Thread:
    """Get a thread from the given input.

    Args:
        thread: Thread instance, thread ID, or None

    Returns:
        A Thread instance

    """
    if isinstance(thread, Thread):
        return thread
    if isinstance(thread, str):
        return Thread(id=thread)
    return get_current_thread() or Thread()
