"""Database management for persistence.

This module provides utilities for managing database sessions and migrations.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from pydantic import TypeAdapter
from pydantic_ai.messages import RetryPromptPart
from pydantic_ai.usage import Usage
from sqlalchemy import JSON, TIMESTAMP, ForeignKey, String, TypeDecorator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.pool import StaticPool

from marvin.settings import settings

from .engine.llm import Message

message_adapter: TypeAdapter[Message] = TypeAdapter(Message)
usage_adapter: TypeAdapter[Usage] = TypeAdapter(Usage)

# Module-level cache for engines and sessionmakers
_async_engine_cache: dict[Any, AsyncEngine] = {}


def serialize_message(message: Message) -> str:
    """
    The `ctx` field in the `RetryPromptPart` is optionally dict[str, Any], which is not always serializable.
    """
    for part in message.parts:
        if isinstance(part, RetryPromptPart):
            if isinstance(part.content, list):
                for content in part.content:
                    content["ctx"] = {
                        k: str(v) for k, v in (content.get("ctx", None) or {}).items()
                    }
    return message_adapter.dump_python(message, mode="json")


def get_async_engine() -> AsyncEngine:
    """Get the SQLAlchemy engine for async operations.

    For SQLite databases, this uses aiosqlite.
    For other databases (e.g. PostgreSQL), this uses the provided URL directly.

    The engine is cached by asyncio event loop to maintain compatibility with run_sync.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop not in _async_engine_cache:
        url = settings.database_url
        if url is None:
            raise ValueError("Database URL is not configured")

        parsed_url = urlparse(url)

        # Handle SQLite databases (default)
        if parsed_url.scheme == "sqlite":
            engine = create_async_engine(
                url,
                echo=False,
                poolclass=StaticPool if url.endswith(":memory:") else None,
                connect_args={"check_same_thread": False},
            )
        # Handle other databases (use URL as-is)
        else:
            engine = create_async_engine(url, echo=False)

        _async_engine_cache[loop] = engine

    return _async_engine_cache[loop]


def set_async_engine(engine: AsyncEngine) -> None:
    """Set the SQLAlchemy engine for async operations."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    _async_engine_cache[loop] = engine


def utc_now() -> datetime:
    """Get the current UTC timestamp."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class DBThread(Base):
    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_thread_id: Mapped[str | None] = mapped_column(ForeignKey("threads.id"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=utc_now
    )

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
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=utc_now
    )

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
            message=serialize_message(message),
            llm_call_id=llm_call_id,
        )


class UsageType(TypeDecorator[Usage]):
    """Custom type for Usage objects that stores them as JSON in the database."""

    impl = JSON
    cache_ok = True

    def process_bind_param(
        self, value: Usage | None, dialect: Any
    ) -> dict[str, Any] | None:
        """Convert Usage to JSON before storing in DB."""
        if value is None:
            return None
        return usage_adapter.dump_python(value, mode="json")

    def process_result_value(
        self, value: dict[str, Any] | None, dialect: Any
    ) -> Usage | None:
        """Convert JSON back to Usage when loading from DB."""
        if value is None:
            return None
        return usage_adapter.validate_python(value)


class DBLLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[str] = mapped_column(ForeignKey("threads.id"), index=True)
    usage: Mapped[Usage] = mapped_column(UsageType)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=utc_now
    )

    messages: Mapped[list[DBMessage]] = relationship(back_populates="llm_call")
    thread: Mapped[DBThread] = relationship(back_populates="llm_calls")

    @classmethod
    async def create(
        cls,
        thread_id: str,
        usage: Usage,
        session: AsyncSession | None = None,
    ) -> "DBLLMCall":
        """Create a new LLM call record.

        Args:
            thread_id: ID of the thread this call belongs to
            usage: Usage information from the model
            session: Optional database session. If not provided, a new one will be created.

        Returns:
            The created DBLLMCall instance
        """
        llm_call = cls(thread_id=thread_id, usage=usage)

        if session is None:
            # Use the sessionmaker pattern for more consistent session management
            async with get_async_session() as session:
                async with session.begin():
                    session.add(llm_call)
                await session.refresh(llm_call)
                return llm_call
        else:
            session.add(llm_call)
            await session.commit()
            await session.refresh(llm_call)
            return llm_call


def ensure_sqlite_memory_tables_exist():
    """Initialize database tables if they don't exist yet.

    For in-memory databases, tables are always created since each connection
    starts with a fresh database. For file-based databases, tables are only
    created if they don't exist.
    """

    # Call init_database which handles all database types
    init_database()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session.

    This uses the async_sessionmaker pattern for more consistent session management.
    """
    engine = get_async_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_db_and_tables(*, force: bool = False) -> None:
    """Create all database tables.

    Args:
        force: If True, drops all existing tables before creating new ones.
    """
    from marvin.utilities.logging import get_logger

    logger = get_logger(__name__)

    engine = get_async_engine()
    async with engine.begin() as conn:
        if force:
            await conn.run_sync(Base.metadata.drop_all)
            logger.debug("Database tables dropped.")

        await conn.run_sync(Base.metadata.create_all)
        logger.debug("Database tables created.")


def init_database():
    """Initialize the database.

    This function should be called during application startup to ensure
    database tables exist before they are accessed.
    """
    from marvin.utilities.logging import get_logger

    logger = get_logger(__name__)

    logger.debug("Initializing database...")
    asyncio.run(create_db_and_tables(force=False))
    logger.debug("Database initialization complete.")
