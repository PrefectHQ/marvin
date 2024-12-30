"""
SQLModel interfaces for persistence.

This module provides SQLModel interfaces for tracking threads, messages, and LLM calls.
"""

from datetime import datetime, UTC
import json
import uuid
from typing import Optional, Dict, Any, List
from sqlmodel import Field, SQLModel, JSON, Column, Relationship, select
from pydantic import TypeAdapter, field_serializer, field_validator

from .database import get_async_session
from .llm import Message

# Message serialization adapter
message_adapter = TypeAdapter(Message)


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


class DBTemplate(SQLModel, table=True):
    """A reusable prompt template."""

    __tablename__ = "templates"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="Unique identifier for this template",
    )
    name: str = Field(index=True, description="User-provided template identifier")
    content: str = Field(description="Template content with variable placeholders")
    version: str = Field(index=True, description="Hash of content for comparison")
    created_at: datetime = Field(
        default_factory=utc_now, description="When this template was created"
    )

    @classmethod
    async def create(cls, name: str, content: str, version: str) -> "DBTemplate":
        """Create a new template."""
        async with get_async_session() as session:
            template = cls(name=name, content=content, version=version)
            session.add(template)
            await session.commit()
            await session.refresh(template)
            return template

    @classmethod
    async def get(cls, template_id: uuid.UUID) -> Optional["DBTemplate"]:
        """Get a template by ID."""
        async with get_async_session() as session:
            return await session.get(cls, template_id)

    @classmethod
    async def get_by_name_and_version(
        cls, name: str, version: str
    ) -> Optional["DBTemplate"]:
        """Get a template by name and version."""
        async with get_async_session() as session:
            query = select(cls).where(cls.name == name, cls.version == version)
            result = await session.execute(query)
            results = result.scalars().all()
            return results[0] if results else None

    async def delete(self) -> None:
        """Delete this template."""
        async with get_async_session() as session:
            await session.delete(self)
            await session.commit()


class DBThread(SQLModel, table=True):
    """A conversation thread that can branch and evolve."""

    __tablename__ = "threads"

    id: str = Field(
        primary_key=True,
        description="Unique identifier for this thread",
    )
    parent_thread_id: Optional[str] = Field(
        default=None,
        foreign_key="threads.id",
        description="Parent thread ID for branching conversations",
    )
    created_at: datetime = Field(
        default_factory=utc_now, description="When this thread was created"
    )
    messages: List["DBMessage"] = Relationship(back_populates="thread")

    @classmethod
    async def create(cls, parent_thread_id: Optional[str] = None) -> "DBThread":
        """Create a new thread."""
        async with get_async_session() as session:
            thread = cls(id=str(uuid.uuid4()), parent_thread_id=parent_thread_id)
            session.add(thread)
            await session.commit()
            await session.refresh(thread)
            return thread

    @classmethod
    async def get(cls, thread_id: str) -> Optional["DBThread"]:
        """Get a thread by ID."""
        async with get_async_session() as session:
            return await session.get(cls, thread_id)

    @classmethod
    async def get_or_create(cls, thread_id: str) -> "DBThread":
        """Get an existing thread or create a new one."""
        thread = await cls.get(thread_id)
        if not thread:
            async with get_async_session() as session:
                thread = cls(id=thread_id)
                session.add(thread)
                await session.commit()
                await session.refresh(thread)
        return thread

    async def delete(self) -> None:
        """Delete this thread and all associated messages."""
        async with get_async_session() as session:
            await session.delete(self)
            await session.commit()


class DBMessage(SQLModel, table=True):
    """A message in the conversation history."""

    __tablename__ = "messages"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="Unique identifier for this message",
    )
    thread_id: str = Field(
        foreign_key="threads.id",
        index=True,
        description="Thread this message belongs to",
    )
    llm_call_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="llm_calls.id",
        description="LLM call that generated this message, if AI-generated",
    )
    message: Message = Field(
        sa_column=Column(JSON),
        description="Serialized message data",
    )
    timestamp: datetime = Field(
        default_factory=utc_now, description="When this message was created"
    )
    thread: "DBThread" = Relationship(back_populates="messages")
    llm_call: Optional["DBLLMCall"] = Relationship(back_populates="messages")

    @field_validator("message")
    @classmethod
    def validate_message(cls, message: Message) -> Message:
        """Validate the message."""
        return json.loads(message_adapter.dump_json(message))

    @field_serializer("message")
    def serialize_message(self, message: Message) -> Dict[str, Any]:
        """Serialize the message to a JSON-compatible dictionary."""
        return json.loads(message_adapter.dump_json(message))

    @classmethod
    async def create(
        cls,
        thread_id: str,
        message: Message,
        llm_call_id: Optional[uuid.UUID] = None,
    ) -> "DBMessage":
        """Create a new message."""
        async with get_async_session() as session:
            db_message = cls.model_validate(
                {
                    "thread_id": thread_id,
                    "message": message,
                    "llm_call_id": llm_call_id,
                }
            )
            session.add(db_message)
            await session.commit()
            await session.refresh(db_message)
            return db_message

    @classmethod
    async def get(cls, message_id: uuid.UUID) -> Optional["DBMessage"]:
        """Get a message by ID."""
        async with get_async_session() as session:
            return await session.get(cls, message_id)

    @classmethod
    async def get_thread_messages(
        cls,
        thread_id: str,
        limit: int = 100,
        before: Optional[datetime] = None,
    ) -> List["DBMessage"]:
        """Get messages for a thread."""
        async with get_async_session() as session:
            query = select(cls).where(cls.thread_id == thread_id)
            if before:
                query = query.where(cls.timestamp <= before)
            query = query.order_by(cls.timestamp).limit(limit)
            result = await session.execute(query)
            return result.scalars().all()

    async def delete(self) -> None:
        """Delete this message."""
        async with get_async_session() as session:
            await session.delete(self)
            await session.commit()


class DBLLMCall(SQLModel, table=True):
    """An API call to the LLM."""

    __tablename__ = "llm_calls"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="Unique identifier for this LLM call",
    )
    thread_id: str = Field(
        foreign_key="threads.id", index=True, description="Thread this call belongs to"
    )
    model: str = Field(index=True, description="Model identifier (e.g. gpt-4)")
    prompt: Dict[str, Any] = Field(
        sa_column=Column(JSON), description="Complete prompt with messages and metadata"
    )
    cost: dict = Field(
        sa_column=Column(JSON),
        description="Cost details for this call",
    )
    timestamp: datetime = Field(
        default_factory=utc_now, description="When this call was made"
    )
    messages: List[DBMessage] = Relationship(back_populates="llm_call")

    @classmethod
    async def create(
        cls,
        thread_id: str,
        model: str,
        prompt: Dict[str, Any],
        response,
    ) -> "DBLLMCall":
        """Create a new LLM call."""
        async with get_async_session() as session:
            llm_call = cls(
                thread_id=thread_id,
                model=model,
                prompt=prompt,
                response=response,
            )
            session.add(llm_call)
            await session.commit()
            await session.refresh(llm_call)
            return llm_call

    @classmethod
    async def get(cls, llm_call_id: uuid.UUID) -> Optional["DBLLMCall"]:
        """Get an LLM call by ID."""
        async with get_async_session() as session:
            return await session.get(cls, llm_call_id)

    async def delete(self) -> None:
        """Delete this LLM call."""
        async with get_async_session() as session:
            await session.delete(self)
            await session.commit()
