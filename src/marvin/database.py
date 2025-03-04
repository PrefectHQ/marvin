"""Database management for persistence.

This module provides utilities for managing database sessions and migrations.
"""

import asyncio
import copy
import inspect
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from pydantic import TypeAdapter
from pydantic_ai.messages import BinaryContent, RetryPromptPart
from pydantic_ai.usage import Usage
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    ForeignKey,
    ForeignKeyConstraint,
    LargeBinary,
    String,
    TypeDecorator,
    func,
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
message_adapter: TypeAdapter[PydanticAIMessage] = TypeAdapter(PydanticAIMessage)
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

    thread: Mapped[DBThread] = relationship(back_populates="messages")
    llm_call_mappings: Mapped[list[DBLLMCallMessage]] = relationship(
        back_populates="message"
    )

    binary_contents: Mapped[list["DBBinaryContent"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="joined",  # Use eager loading to avoid detached instance issues
    )

    @classmethod
    def from_message(
        cls,
        thread_id: str,
        message: PydanticAIMessage,
        created_at: datetime | None = None,
    ) -> "DBMessage":
        # Make a copy of the message to avoid modifying the original
        message_copy = copy.deepcopy(message)
        binary_contents = []

        # Process parts to extract binary content
        if message.kind == "request":
            for part_idx, part in enumerate(message_copy.parts):
                if part.part_kind == "user-prompt" and isinstance(part.content, list):
                    # Store a new list to replace the original
                    new_content = []

                    # For each content item in the user prompt
                    for content_idx, content in enumerate(part.content):
                        if isinstance(content, BinaryContent):
                            # Create binary content record
                            binary_content = DBBinaryContent(
                                part_index=part_idx,
                                content_index=content_idx,
                                data=content.data,
                                media_type=content.media_type,
                            )
                            binary_contents.append(binary_content)

                            # Replace binary content with a string placeholder that won't cause validation errors
                            new_content.append(
                                f"[Binary content: {content.media_type}]"
                            )
                        else:
                            # Keep non-binary content as is
                            new_content.append(content)

                    # Replace the entire content list
                    part.content = new_content

        # Create the message DB record
        db_message = cls(
            thread_id=thread_id,
            message=serialize_message(message_copy),
            created_at=created_at or utc_now(),
        )

        # Attach binary contents
        for binary_content in binary_contents:
            binary_content.message = db_message

        return db_message

    def to_message(self) -> "Message":
        """Convert a database message to a thread message."""
        import marvin.thread

        # Get the basic message
        message_dict = message_adapter.validate_python(self.message)

        # Restore binary content if any exists
        if (
            hasattr(self, "binary_contents")
            and self.binary_contents
            and message_dict.kind == "request"
        ):
            for binary_content in self.binary_contents:
                if 0 <= binary_content.part_index < len(message_dict.parts):
                    part = message_dict.parts[binary_content.part_index]
                    if (
                        part.part_kind == "user-prompt"
                        and isinstance(part.content, list)
                        and 0 <= binary_content.content_index < len(part.content)
                    ):
                        # Replace placeholder with actual binary content
                        part.content[binary_content.content_index] = BinaryContent(
                            data=binary_content.data,
                            media_type=binary_content.media_type,
                        )

        return marvin.thread.Message(
            id=self.id,
            thread_id=self.thread_id,
            message=message_dict,
            created_at=self.created_at,
        )


class DBBinaryContent(Base):
    __tablename__ = "binary_contents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"), index=True)
    part_index: Mapped[int] = (
        mapped_column()
    )  # Index of the part containing this binary content
    content_index: Mapped[int] = mapped_column()  # Index within the content array
    data: Mapped[bytes] = mapped_column(LargeBinary)
    media_type: Mapped[str] = mapped_column(String)

    __table_args__ = (
        ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name="fk_binary_contents_message_id",
        ),
    )

    message: Mapped[DBMessage] = relationship(back_populates="binary_contents")


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
    if session is not None:
        yield session
        return

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


async def create_db_and_tables(*, force: bool = False) -> None:
    """Create all database tables synchronously.

    This is a synchronous alternative to create_db_and_tables() that can be used
    in contexts where asyncio.run() cannot be called.

    Args:
        force: If True, drops all existing tables before creating new ones.
    """
    engine = get_async_engine()

    async with engine.begin() as conn:
        if force:
            await conn.run_sync(Base.metadata.drop_all)
            logger.debug("Database tables dropped.")

        if force:
            await conn.run_sync(Base.metadata.drop_all)
            logger.debug("Database tables dropped.")

        await conn.run_sync(Base.metadata.create_all)
        logger.debug("Database tables created.")


def init_database_if_necessary():
    """Initialize the database.

    This function handles database initialization differently based on the type:
    - File-based SQLite: If file doesn't exist, create it and run migrations
    - Other databases: No automatic initialization
    """
    global db_initialized
    if not db_initialized:
        if not settings.auto_init_sqlite:
            return

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

                    # Create empty file to ensure directory exists
                    db_file.touch()

                    # Run migrations to create schema
                    if _run_migrations():
                        logger.info(
                            f'[green]A new SQLite database was created at "{path}" and migrations were applied successfully.[/]',
                            extra={"markup": True},
                        )
                    else:
                        logger.warning(
                            f'[yellow]A new SQLite database was created at "{path}" but migrations failed.[/]',
                            extra={"markup": True},
                        )

        db_initialized = True
