"""Database management for persistence.

This module provides utilities for managing database sessions and migrations.
"""

import uuid
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import TypeAdapter
from pydantic_ai.usage import Usage
from sqlalchemy import JSON, ForeignKey, String, TypeDecorator, create_engine, inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
)

from marvin.settings import settings

from .engine.llm import Message

message_adapter: TypeAdapter[Message] = TypeAdapter(Message)
usage_adapter: TypeAdapter[Usage] = TypeAdapter(Usage)

# Module-level cache for engines
_engine_cache = {}
_async_engine_cache = {}


def get_engine():
    """Get the SQLAlchemy engine for sync operations."""
    if "default" not in _engine_cache:
        _engine_cache["default"] = create_engine(
            f"sqlite:///{settings.database_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engine_cache["default"]


def get_async_engine():
    """Get the SQLAlchemy engine for async operations."""
    if "default" not in _async_engine_cache:
        _async_engine_cache["default"] = create_async_engine(
            f"sqlite+aiosqlite:///{settings.database_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _async_engine_cache["default"]


def set_engine(engine):
    """Set the SQLAlchemy engine for sync operations."""
    _engine_cache["default"] = engine


def set_async_engine(engine):
    """Set the SQLAlchemy engine for async operations."""
    _async_engine_cache["default"] = engine


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class DBThread(Base):
    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_thread_id: Mapped[str | None] = mapped_column(ForeignKey("threads.id"))
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    messages: Mapped[list["DBMessage"]] = relationship(back_populates="thread")
    llm_calls: Mapped[list["DBLLMCall"]] = relationship(back_populates="thread")

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        id: str | None = None,
        parent_thread_id: str | None = None,
    ) -> "DBThread":
        """Create a new thread record.

        Args:
            session: Database session to use
            id: Optional ID to use for the thread. If not provided, a UUID will be generated.
            parent_thread_id: Optional ID of the parent thread

        Returns:
            The created DBThread instance
        """
        thread = cls(
            id=id or str(uuid.uuid4()),
            parent_thread_id=parent_thread_id,
        )
        session.add(thread)
        await session.commit()
        await session.refresh(thread)
        return thread


class DBMessage(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[str] = mapped_column(ForeignKey("threads.id"), index=True)
    llm_call_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("llm_calls.id"),
        default=None,
    )
    message: Mapped[dict[str, Any]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(default=utc_now)

    thread: Mapped[DBThread] = relationship(back_populates="messages")
    llm_call: Mapped[Optional["DBLLMCall"]] = relationship(back_populates="messages")

    @classmethod
    def from_message(
        cls,
        thread_id: str,
        message: Message,
        llm_call_id: uuid.UUID | None = None,
    ) -> "DBMessage":
        return cls(
            thread_id=thread_id,
            message=message_adapter.dump_python(message, mode="json"),
            llm_call_id=llm_call_id,
        )


class UsageType(TypeDecorator):
    """Custom type for Usage objects that stores them as JSON in the database."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: Usage | None, dialect) -> dict | None:
        """Convert Usage to JSON before storing in DB."""
        if value is None:
            return None
        return usage_adapter.dump_python(value, mode="json")

    def process_result_value(self, value: dict | None, dialect) -> Usage | None:
        """Convert JSON back to Usage when loading from DB."""
        if value is None:
            return None
        return usage_adapter.validate_python(value)


class DBLLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[str] = mapped_column(ForeignKey("threads.id"), index=True)
    # prompt: Mapped[dict[str, Any]] = mapped_column(JSON)
    usage: Mapped[Usage] = mapped_column(UsageType)
    timestamp: Mapped[datetime] = mapped_column(default=utc_now)

    messages: Mapped[list[DBMessage]] = relationship(back_populates="llm_call")
    thread: Mapped[DBThread] = relationship(back_populates="llm_calls")

    @classmethod
    async def create(
        cls,
        thread_id: str,
        # prompt: dict[str, Any],
        usage: Usage,
        session: AsyncSession | None = None,
    ) -> "DBLLMCall":
        """Create a new LLM call record.

        Args:
            thread_id: ID of the thread this call belongs to
            prompt: The prompt sent to the model
            usage: Usage information from the model
            session: Optional database session. If not provided, a new one will be created.

        Returns:
            The created DBLLMCall instance
        """
        llm_call = cls(thread_id=thread_id, usage=usage)

        if session is None:
            async with get_async_session() as session:
                session.add(llm_call)
                await session.commit()
                await session.refresh(llm_call)
                return llm_call
        else:
            session.add(llm_call)
            await session.commit()
            await session.refresh(llm_call)
            return llm_call


def ensure_tables_exist():
    """Initialize database tables if they don't exist yet."""
    inspector = inspect(get_engine())
    if not inspector.get_table_names():
        Base.metadata.create_all(get_engine())


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session."""
    session = Session(get_engine())
    try:
        yield session
    finally:
        session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    session = AsyncSession(get_async_engine())
    try:
        yield session
    finally:
        await session.close()


def create_db_and_tables(*, force: bool = False):
    """Create all database tables.

    Args:
        force: If True, drops all existing tables before creating new ones.

    """
    if force:
        Base.metadata.drop_all(get_engine())
        print("Database tables dropped.")
    Base.metadata.create_all(get_engine())
    print("Database tables created.")
