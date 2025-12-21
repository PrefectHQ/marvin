"""Database management for persistence.

This module provides utilities for managing database sessions and migrations.
"""

import asyncio
import inspect
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from pydantic import ConfigDict, TypeAdapter
from pydantic_ai.messages import RetryPromptPart
from pydantic_ai.usage import Usage
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    ForeignKey,
    Index,
    String,
    TypeDecorator,
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

import marvin
from marvin.settings import settings
from marvin.utilities.logging import get_logger

from .engine.llm import PydanticAIMessage

if TYPE_CHECKING:
    from marvin.thread import Message

logger = get_logger(__name__)
message_adapter: TypeAdapter[PydanticAIMessage] = TypeAdapter(
    PydanticAIMessage,
    config=ConfigDict(ser_json_bytes="base64", val_json_bytes="base64"),
)
usage_adapter: TypeAdapter[Usage] = TypeAdapter(Usage)

# Module-level cache for engines and sessionmakers
_async_engine_cache: dict[Any, AsyncEngine] = {}
db_initialized = False

# Migration constants
MARVIN_DIR = Path(marvin.__file__).parent.parent.parent
ALEMBIC_DIR = MARVIN_DIR / "migrations"
ALEMBIC_INI = MARVIN_DIR / "alembic.ini"


def serialize_message(message: PydanticAIMessage) -> str:
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

        # Handle SQLite databases (default)
        if is_sqlite():
            engine = create_async_engine(url, echo=False)
        # Handle other databases (use URL as-is)
        else:
            engine = create_async_engine(url, echo=False)

        _async_engine_cache[loop] = engine

    return _async_engine_cache[loop]


def is_sqlite() -> bool:
    """Check if the configured database is SQLite."""
    url = settings.database_url
    if url is None:
        raise ValueError("Database URL is not configured")

    parsed_url = urlparse(url)
    return parsed_url.scheme.startswith("sqlite")


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
        session: AsyncSession | None = None,
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
        async with get_async_session(session) as session:
            thread = cls(
                id=id or str(uuid.uuid4()),
                parent_thread_id=parent_thread_id,
            )
            session.add(thread)
        return thread


class DBLLMCallMessage(Base):
    """Mapping table between LLM calls and messages."""

    __tablename__ = "llm_call_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    llm_call_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("llm_calls.id"), index=True
    )
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"), index=True)
    in_initial_prompt: Mapped[bool] = mapped_column()
    order: Mapped[int] = mapped_column()  # Track message order within the call

    llm_call: Mapped["DBLLMCall"] = relationship(back_populates="message_mappings")
    message: Mapped["DBMessage"] = relationship(back_populates="llm_call_mappings")


class DBMessage(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[str] = mapped_column(ForeignKey("threads.id"))
    message: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=utc_now, server_default=func.now()
    )

    # Create a composite index on thread_id and timestamp in descending order
    # Using SQLAlchemy's proper syntax for descending index
    __table_args__ = (
        Index(
            "ix_messages_thread_id_created_at_desc",
            "thread_id",
            created_at.desc(),
        ),
    )

    thread: Mapped[DBThread] = relationship(back_populates="messages")
    llm_call_mappings: Mapped[list[DBLLMCallMessage]] = relationship(
        back_populates="message"
    )

    @classmethod
    def from_message(
        cls,
        thread_id: str,
        message: PydanticAIMessage,
        created_at: datetime | None = None,
    ) -> "DBMessage":
        return cls(
            thread_id=thread_id,
            message=serialize_message(message),
            created_at=created_at or utc_now(),
        )

    def to_message(self) -> "Message":
        import marvin.thread

        return marvin.thread.Message(
            id=self.id,
            thread_id=self.thread_id,
            message=message_adapter.validate_python(self.message),
            created_at=self.created_at,
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

    message_mappings: Mapped[list[DBLLMCallMessage]] = relationship(
        back_populates="llm_call"
    )
    thread: Mapped[DBThread] = relationship(back_populates="llm_calls")

    @classmethod
    async def create(
        cls,
        thread_id: str,
        usage: Usage,
        prompt_messages: list["DBMessage | Message"] | None = None,
        completion_messages: list["DBMessage | Message"] | None = None,
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
        llm_call_id = uuid.uuid4()
        llm_call = cls(id=llm_call_id, thread_id=thread_id, usage=usage)

        async with get_async_session(session) as session:
            session.add(llm_call)

            # Add request messages, maintaining their original order
            for i, message in enumerate(prompt_messages):
                mapping = DBLLMCallMessage(
                    llm_call_id=llm_call.id,
                    message_id=message.id,
                    in_initial_prompt=True,
                    order=i,  # Set order based on position in the list
                )
                session.add(mapping)

            # Add response messages, maintaining their original order
            # Response messages come after request messages in order
            start_order = len(prompt_messages)
            for i, message in enumerate(completion_messages):
                mapping = DBLLMCallMessage(
                    llm_call_id=llm_call.id,
                    message_id=message.id,
                    in_initial_prompt=False,
                    order=start_order + i,  # Continue numbering after request messages
                )
                session.add(mapping)

        return llm_call


@asynccontextmanager
async def get_async_session(
    session: AsyncSession | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session.

    This uses the async_sessionmaker pattern for more consistent session management.
    If a session is provided, it is returned as-is.

    Args:
        session: An optional existing session to use. If provided, this function
            will yield it directly instead of creating a new one.

    Yields:
        An async SQLAlchemy session
    """
    # If session is provided, just use it
    if session is not None:
        yield session
        return

    # Try to get the engine - if this fails because tables don't exist,
    # make sure to create them before proceeding
    engine = get_async_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Create a session
    async with session_factory() as session:
        try:
            # Check if tables exist by attempting a simple query
            if is_sqlite():
                try:
                    # Try to query the threads table to see if it exists
                    await session.execute(select(DBThread).limit(1))
                except Exception as e:
                    if "no such table" in str(e).lower():
                        # Tables don't exist, create them
                        logger.warning("Database tables don't exist, creating them now")
                        async with engine.begin() as conn:
                            await conn.run_sync(Base.metadata.create_all)
                            logger.info("Created database tables on first access")

            # Now yield the session
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _run_migrations(alembic_log_level: str = "WARNING") -> bool:
    """Run Alembic migrations.

    Returns:
        True if migrations were successful, False otherwise.
    """
    from alembic import command

    from marvin.cli.migrations import get_alembic_cfg

    alembic_cfg = get_alembic_cfg()
    try:
        command.upgrade(alembic_cfg, "head")
        return True
    except RuntimeError as e:
        if "event loop" in str(e):
            logger.warning(
                inspect.cleandoc(
                    """Migrations can not be run from inside an async context.
                    This is unusual and means you are importing Marvin within an
                    async function and it is trying to automatically create a
                    SQLite database that doesn't already exist. Make sure you
                    create, manage, or migrate your Marvin database separately.
                    You can set MARVIN_AUTO_INIT_SQLITE=false to disable this
                    behavior."""
                )
            )
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        return False


async def create_db_and_tables(
    *, force: bool = False, dispose_engine: bool = False
) -> None:
    """Create all database tables.

    Args:
        force: If True, drops all existing tables before creating new ones.
        dispose_engine: If True, dispose the engine after creating tables.
            This is useful when called from asyncio.run() to ensure the
            aiosqlite worker thread is cleaned up and doesn't prevent
            Python from exiting.
    """
    engine = get_async_engine()

    async with engine.begin() as conn:
        if force:
            await conn.run_sync(Base.metadata.drop_all)
            logger.debug("Database tables dropped.")

        await conn.run_sync(Base.metadata.create_all)
        logger.debug("Database tables created.")

    if dispose_engine:
        await engine.dispose()
        # Remove the engine from the cache since it's disposed
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        _async_engine_cache.pop(loop, None)


def init_database_if_necessary():
    """Initialize the database file if necessary.

    This function only handles creating the database file and parent directories,
    it does not create tables. Tables are created by ensure_db_tables_exist().
    """
    global db_initialized
    if not db_initialized:
        if is_sqlite():
            # For file-based SQLite, check if file exists
            url = settings.database_url
            if url is None:
                return

            parsed_url = urlparse(url)
            if parsed_url.path and parsed_url.path != ":memory:":
                # Strip the leading slash if present
                path = parsed_url.path
                if path.startswith("/"):
                    path = path[1:]

                db_file = Path(path)
                if not db_file.exists():
                    # Create parent directories if needed
                    db_file.parent.mkdir(parents=True, exist_ok=True)
                    # Create empty file
                    db_file.touch()
                    logger.debug(f"Created new SQLite database file at {path}")

        db_initialized = True


def ensure_db_tables_exist():
    """Ensure database tables exist, creating them if necessary.

    This function creates all database tables directly without using migrations,
    which is more reliable than using Alembic migrations.
    """
    # First initialize the database file if needed
    init_database_if_necessary()

    # Now create tables
    import asyncio
    import sqlite3
    import threading

    # Define a lock for thread safety
    _create_tables_lock = threading.Lock()

    # Check if we're already in an event loop
    try:
        asyncio.get_running_loop()
        in_async_context = True
    except RuntimeError:
        in_async_context = False

    # Thread-local check to avoid recursion in async context
    if in_async_context:
        # If we're in an async context, we need to use a synchronous approach
        # Otherwise, we'll get "Event loop is already running" errors
        try:
            # For SQLite, we can directly check if tables exist
            if is_sqlite():
                url = settings.database_url
                if url is None:
                    return

                # Parse the URL to get the database path
                parsed_url = urlparse(url)
                if parsed_url.path and parsed_url.path != ":memory:":
                    # Strip the leading slash if present
                    path = parsed_url.path
                    if path.startswith("/"):
                        path = path[1:]

                    # Direct SQLite connection to check tables
                    try:
                        with _create_tables_lock:
                            conn = sqlite3.connect(path)
                            cursor = conn.cursor()
                            # Check if the threads table exists
                            cursor.execute(
                                "SELECT name FROM sqlite_master WHERE type='table' AND name='threads'"
                            )
                            result = cursor.fetchone()

                            if not result:
                                # Tables don't exist, we'll need to create them later
                                logger.warning(
                                    "Database tables don't exist, but we're in an async context. "
                                    "Tables will be created on first database access."
                                )
                            else:
                                logger.debug("Database tables already exist.")

                            conn.close()
                    except sqlite3.Error as e:
                        logger.error(f"Error checking database tables: {e}")

            return  # Return early if in async context
        except Exception as e:
            logger.error(f"Error ensuring database tables exist: {e}")
            return

    # Create tables synchronously using asyncio.run() if we're not in an async context
    try:
        with _create_tables_lock:
            # Use dispose_engine=True to clean up the aiosqlite worker thread
            # after table creation. Without this, the cached engine's worker
            # thread could prevent Python from exiting cleanly.
            asyncio.run(create_db_and_tables(dispose_engine=True))
            logger.debug("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
