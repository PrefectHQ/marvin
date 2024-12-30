"""
Thread management for conversations.

This module provides the Thread class for managing conversation context.
"""

from datetime import datetime, UTC
import uuid
from typing import Optional, List
from contextvars import ContextVar
from sqlmodel import select

from .database import get_async_session
from .models import DBThread, DBMessage, message_adapter
from .llm import Message, UserMessage


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


# Global context var for current thread
current_thread: ContextVar[Optional["Thread"]] = ContextVar(
    "current_thread", default=None
)


class Thread:
    """Main runtime object for managing conversation context."""

    def __init__(
        self,
        id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ):
        """Initialize a thread.

        Args:
            id: Optional thread ID. If not provided, a new one will be created.
            parent_id: Optional parent thread ID for branching conversations.
        """
        self.id = id or str(uuid.uuid4())
        self.parent_id = parent_id
        self._db_thread: Optional[DBThread] = None

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

    async def add_messages(self, messages: list[Message]):
        """Add multiple messages to the thread.

        Args:
            messages: List of messages to add (UserMessage, AssistantMessage, etc.)
        """
        await self._ensure_thread_exists()

        async with get_async_session() as session:
            for message in messages:
                db_message = DBMessage.model_validate(
                    {
                        "thread_id": self.id,
                        "message": message,
                    }
                )
                session.add(db_message)
            await session.commit()

    async def add_user_message(self, message: str):
        """Add a user message to the thread."""
        await self.add_messages([UserMessage(content=message)])

    async def get_messages(
        self, include_parent: bool = True, include_system_messages: bool = False
    ) -> List[Message]:
        """Get all messages in this thread.

        Args:
            include_parent: Whether to include messages from parent thread
            include_system_messages: Whether to include system messages in the response
        """
        await self._ensure_thread_exists()

        async with get_async_session() as session:
            # Get messages for current thread
            query = select(DBMessage).where(DBMessage.thread_id == self.id)
            query = query.order_by(DBMessage.timestamp)
            result = await session.exec(query)
            messages: list[Message] = [
                message_adapter.validate_python(m.message) for m in result.all()
            ]

            # Get parent messages if requested
            if include_parent and self.parent_id:
                parent = await session.get(DBThread, self.parent_id)
                if parent:
                    parent_query = select(DBMessage).where(
                        DBMessage.thread_id == self.parent_id,
                        DBMessage.timestamp <= self._db_thread.created_at,
                    )
                    parent_query = parent_query.order_by(DBMessage.timestamp)
                    parent_result = await session.exec(parent_query)
                    parent_messages = [
                        message_adapter.validate_python(m.message)
                        for m in parent_result.all()
                    ]
                    messages = parent_messages + messages

        return messages

    def __enter__(self):
        """Set this thread as the current thread in context."""
        self._token = current_thread.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
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
