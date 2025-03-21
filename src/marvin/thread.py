"""Thread management for conversations.

This module provides the Thread class for managing conversation context.
"""

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Sequence

from pydantic import TypeAdapter
from pydantic_ai.messages import UserContent
from pydantic_ai.usage import Usage
from sqlalchemy import select

from marvin.database import (
    DBLLMCall,
    DBLLMCallMessage,
    DBMessage,
    DBThread,
    get_async_session,
    utc_now,
)
from marvin.engine.llm import ModelRequest
from marvin.utilities.asyncio import run_sync

from .engine.llm import AgentMessage, PydanticAIMessage, SystemMessage, UserMessage

# Message serialization adapter
message_adapter: TypeAdapter[PydanticAIMessage | list[PydanticAIMessage]] = TypeAdapter(
    PydanticAIMessage | list[PydanticAIMessage]
)


@dataclass(kw_only=True)
class Message:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    thread_id: str = field(default=None)
    message: PydanticAIMessage
    created_at: datetime = field(default_factory=utc_now)


@dataclass(kw_only=True)
class LLMCallMessages:
    prompt: list[Message]
    completion: list[Message]


@dataclass(kw_only=True)
class LLMCall:
    """Represents an LLM call."""

    id: uuid.UUID
    thread_id: str
    usage: Usage
    timestamp: datetime

    def get_messages(self) -> LLMCallMessages:
        """Get the messages for this LLM call."""
        return run_sync(self.get_messages_async())

    async def get_messages_async(self) -> LLMCallMessages:
        """Get the messages for this LLM call."""
        async with get_async_session() as session:
            # Query the llm_call_messages table to get all messages associated with this LLM call

            # Get all message associations for this LLM call ordered by their sequence
            query = (
                select(DBLLMCallMessage, DBMessage)
                .join(
                    DBMessage,
                    DBLLMCallMessage.message_id == DBMessage.id,
                )
                .where(DBLLMCallMessage.llm_call_id == self.id)
                .order_by(DBLLMCallMessage.order)
            )

            result = await session.execute(query)

            # Map the database enum values to our new terminology
            # REQUEST -> prompt, RESPONSE -> completion
            messages_by_role = {"prompt": [], "completion": []}

            for llm_call_message, db_message in result:
                if llm_call_message.in_initial_prompt:
                    messages_by_role["prompt"].append(db_message.to_message())
                else:
                    messages_by_role["completion"].append(db_message.to_message())

            return LLMCallMessages(
                prompt=messages_by_role["prompt"],
                completion=messages_by_role["completion"],
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
    _db_thread: bool = field(default=False, init=False, repr=False)
    _tokens: list[Any] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.id, str):
            raise ValueError("Thread ID must be a string")

    async def _ensure_thread_exists(self) -> None:
        """Ensure thread exists in database."""
        if self._db_thread:
            return

        # First, ensure tables are created in case of missing initialization
        try:
            from marvin.database import ensure_db_tables_exist

            ensure_db_tables_exist()
        except Exception as e:
            from marvin.utilities.logging import get_logger

            logger = get_logger(__name__)
            logger.warning(f"Failed to ensure DB tables exist: {e}")

        # Now we can safely create the thread
        try:
            async with get_async_session() as session:
                db_thread = await session.get(DBThread, self.id)
                if db_thread is not None:
                    self._db_thread = True
                else:
                    await DBThread.create(
                        session=session,
                        id=self.id,
                        parent_thread_id=self.parent_id,
                    )
                    self._db_thread = True
        except Exception as e:
            from marvin.utilities.logging import get_logger

            logger = get_logger(__name__)
            logger.error(f"Failed to create thread in database: {e}")
            # Re-raise to fail fast rather than letting downstream code handle DB errors
            raise

    def add_messages(self, messages: list[PydanticAIMessage]) -> list[Message]:
        """Add multiple messages to the thread.

        Args:
            messages: List of messages to add (UserMessage, AssistantMessage, etc.)
            llm_call_id: Optional ID of the LLM call that generated these messages

        """
        return run_sync(self.add_messages_async(messages))

    async def add_messages_async(
        self, messages: list[PydanticAIMessage]
    ) -> list[Message]:
        """Add multiple messages to the thread.

        Args:
            messages: List of messages to add (UserMessage, AssistantMessage, etc.)
            llm_call_id: Optional ID of the LLM call that generated these messages

        """
        await self._ensure_thread_exists()

        async with get_async_session() as session:
            # Create DB message records
            db_messages = [
                DBMessage.from_message(thread_id=self.id, message=message)
                for message in messages
            ]
            session.add_all(db_messages)

            await session.commit()

        return [db_m.to_message() for db_m in db_messages]

    def add_system_message(self, message: str) -> Message:
        """Add a system message to the thread."""
        return run_sync(self.add_system_message_async(message))

    async def add_system_message_async(self, message: str) -> Message:
        """Add a system message to the thread."""
        messages = await self.add_messages_async([SystemMessage(content=message)])
        return messages[0]

    def add_user_message(self, message: str | Sequence[UserContent]) -> Message:
        """Add a user message to the thread."""
        return run_sync(self.add_user_message_async(message))

    async def add_user_message_async(
        self, message: str | Sequence[UserContent]
    ) -> Message:
        """Add a user message to the thread."""
        messages = await self.add_messages_async([UserMessage(content=message)])
        return messages[0]

    def add_agent_message(self, message: str) -> Message:
        """Add an agent message to the thread."""
        return run_sync(self.add_agent_message_async(message))

    async def add_agent_message_async(self, message: str) -> Message:
        """Add an agent message to the thread."""
        messages = await self.add_messages_async([AgentMessage(content=message)])
        return messages[0]

    def add_info_message(self, message: str, prefix: str = None) -> Message:
        """Add an info message to the thread."""
        return run_sync(self.add_info_message_async(message, prefix=prefix))

    async def add_info_message_async(self, message: str, prefix: str = None) -> Message:
        """Add an info message to the thread."""
        prefix = prefix or "INFO MESSAGE"
        messages = await self.add_messages_async(
            [UserMessage(content=f"{prefix}: {message}")]
        )
        return messages[0]

    def get_messages(
        self,
        before: datetime | None = None,
        after: datetime | None = None,
        limit: int | None = None,
        include_system_messages: bool = False,
    ) -> list[Message]:
        """Get all messages in this thread.

        Args:
            before: Only return messages before this timestamp
            after: Only return messages after this timestamp
            limit: Maximum number of messages to return
            include_system_messages: Whether to include system messages
        Returns:
            List of messages in chronological order
        """
        return run_sync(
            self.get_messages_async(
                before=before,
                after=after,
                limit=limit,
                include_system_messages=include_system_messages,
            ),
        )

    async def get_messages_async(
        self,
        before: datetime | None = None,
        after: datetime | None = None,
        limit: int | None = None,
        include_system_messages: bool = False,
    ) -> list[Message]:
        """Get all messages in this thread.

        Args:
            before: Only return messages before this timestamp
            after: Only return messages after this timestamp
            limit: Maximum number of messages to return
            include_system_messages: Whether to include system messages
        Returns:
            List of messages in chronological order
        """
        await self._ensure_thread_exists()

        async with get_async_session() as session:
            query = (
                select(DBMessage)
                .where(DBMessage.thread_id == self.id)
                .order_by(DBMessage.created_at.desc())
            )

            if before is not None:
                query = query.where(DBMessage.created_at < before)
            if after is not None:
                query = query.where(DBMessage.created_at > after)

            if limit is not None:
                query = query.limit(limit)

            result = await session.execute(query)

            db_messages = list(result.scalars().all())
            db_messages.reverse()

            messages = [db_m.to_message() for db_m in db_messages]

            if not include_system_messages:
                for m in messages:
                    if isinstance(m.message, ModelRequest) and any(
                        p.part_kind == "system-prompt" for p in m.message.parts
                    ):
                        messages.remove(m)

            return messages

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
            return [
                LLMCall(
                    id=call.id,
                    thread_id=call.thread_id,
                    usage=call.usage,
                    timestamp=call.timestamp,
                )
                for call in result.scalars().all()
            ]

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

    This function is intended for debugging purposes only, and will only work in
    certain contexts where the last thread is available in memory.
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
    elif thread is not None:
        return Thread(id=thread)
    else:
        return get_current_thread() or Thread()
