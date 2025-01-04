"""
Thread management for conversations.

This module provides the Thread class for managing conversation context.
"""

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import TypeAdapter
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from marvin.utilities.asyncio import run_sync

from .database import DBMessage, DBThread, get_async_session
from .llm import Message, UserMessage

# Message serialization adapter
message_adapter: TypeAdapter[Message] = TypeAdapter(Message)


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


# Global context var for current thread
current_thread: ContextVar[Optional["Thread"]] = ContextVar(
    "current_thread", default=None
)


@dataclass
class Thread:
    """Main runtime object for managing conversation context."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    _db_thread: Optional[DBThread] = field(default=None, init=False, repr=False)

    async def _ensure_thread_exists(self) -> None:
        """Ensure thread exists in database."""
        if self._db_thread is not None:
            return

        async with get_async_session() as session:
            self._db_thread = await session.get(DBThread, self.id)
            if not self._db_thread:
                self._db_thread = DBThread(id=self.id, parent_thread_id=self.parent_id)
                session.add(self._db_thread)
                await session.commit()
                await session.refresh(self._db_thread)

    def add_messages(self, messages: list[Message]):
        """Add multiple messages to the thread.

        Args:
            messages: List of messages to add (UserMessage, AssistantMessage, etc.)
        """
        return run_sync(self.add_messages_async(messages))

    async def add_messages_async(self, messages: list[Message]):
        """Add multiple messages to the thread.

        Args:
            messages: List of messages to add (UserMessage, AssistantMessage, etc.)
        """
        await self._ensure_thread_exists()

        async with get_async_session() as session:
            for message in messages:
                db_message = DBMessage.from_message(
                    thread_id=self.id,
                    message=message,
                )
                session.add(db_message)
            await session.commit()

    def add_user_message(self, message: str):
        """Add a user message to the thread."""
        return run_sync(self.add_user_message_async(message))

    async def add_user_message_async(self, message: str):
        """Add a user message to the thread."""
        await self.add_messages_async([UserMessage(content=message)])

    async def _get_thread_hierarchy(
        self, session: AsyncSession, max_depth: int = 10
    ) -> list[tuple[str, datetime]]:
        """Get the thread hierarchy (thread_id, created_at) pairs up to max_depth levels.

        Returns:
            List of (thread_id, created_at) pairs, ordered from current thread to oldest ancestor.
        """
        hierarchy: list[tuple[str, datetime]] = []
        current_thread = self._db_thread
        depth = 0

        while current_thread and depth < max_depth:
            hierarchy.append((current_thread.id, current_thread.created_at))
            if not current_thread.parent_thread_id:
                break
            current_thread = await session.get(
                DBThread, current_thread.parent_thread_id
            )
            depth += 1

        return hierarchy

    def get_messages(
        self, include_parent: bool = True, include_system_messages: bool = False
    ) -> list[Message]:
        """Get all messages in this thread."""
        return run_sync(
            self.get_messages_async(include_parent, include_system_messages)
        )

    async def get_messages_async(
        self, include_parent: bool = True, include_system_messages: bool = False
    ) -> list[Message]:
        """Get all messages in this thread.

        Args:
            include_parent: Whether to include messages from parent thread
            include_system_messages: Whether to include system messages in the response
        """
        await self._ensure_thread_exists()

        async with get_async_session() as session:
            if not include_parent:
                # Simple case: just get messages for this thread
                query = select(DBMessage).where(DBMessage.thread_id == self.id)
                query = query.order_by(DBMessage.timestamp)
                result = await session.execute(query)
                return [
                    message_adapter.validate_python(m.message)
                    for m in result.scalars().all()
                ]

            # Get the thread hierarchy
            hierarchy = await self._get_thread_hierarchy(session)
            if not hierarchy:
                return []

            # Build a query that gets messages from all threads in the hierarchy,
            # but only messages that were created before their child thread
            conditions: list[Any] = []
            for i, (thread_id, _) in enumerate(hierarchy):
                if i == 0:  # Current thread - get all messages
                    conditions.append(and_(DBMessage.thread_id == thread_id))
                else:  # Parent thread - get messages before child was created
                    conditions.append(
                        and_(
                            DBMessage.thread_id == thread_id,
                            DBMessage.timestamp <= hierarchy[i - 1][1],
                        )
                    )

            query = select(DBMessage).where(or_(*conditions))
            query = query.order_by(DBMessage.timestamp)
            result = await session.execute(query)

            return [
                message_adapter.validate_python(m.message)
                for m in result.scalars().all()
            ]

    def __enter__(self):
        """Set this thread as the current thread in context."""
        self._token = current_thread.set(self)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        """Reset the current thread in context."""
        current_thread.reset(self._token)

    @classmethod
    def get_current(cls) -> Optional["Thread"]:
        """Get the current thread from context."""
        return current_thread.get()


def get_current_thread() -> Optional[Thread]:
    """Get the currently active thread from context.

    Returns:
        The current Thread instance or None if no thread is active.
    """
    return Thread.get_current()


def get_thread(thread: Thread | str | None) -> Thread:
    """Get a thread from the given input.

    Args:
        thread: Thread instance, thread ID, or None

    Returns:
        A Thread instance
    """
    if isinstance(thread, Thread):
        return thread
    elif isinstance(thread, str):
        return Thread(id=thread)
    else:
        return get_current_thread() or Thread()
