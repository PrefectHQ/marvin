"""
Database models for Marvin.
"""

import os
import uuid
import datetime
from typing import Any, Dict, List, Optional

from pydantic import ConfigDict
from sqlmodel import Field as SQLField, SQLModel, create_engine, Session, JSON, Relationship

# Update settings with database configuration
import marvin
if TYPE_CHECKING:
    from .events import Event

# Database setup
engine = create_engine(f"sqlite:///{marvin.settings.database_path}", echo=False)


class ThreadBase(SQLModel):
    """Base model for conversation threads."""
    id: str = SQLField(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    name: Optional[str] = None
    parent_id: Optional[str] = SQLField(default=None, foreign_key="threads.id")
    metadata: Dict[str, Any] = SQLField(default_factory=dict, sa_column=SQLField(JSON))


class Thread(ThreadBase, table=True):
    """A conversation thread."""
    __tablename__ = "threads"
    
    # Relationships
    events: List["Event"] = Relationship(back_populates="thread")
    parent: Optional["Thread"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs=dict(remote_side="Thread.id"),
    )
    children: List["Thread"] = Relationship(back_populates="parent")


class Agent(SQLModel, table=True):
    """An agent that can participate in conversations."""
    __tablename__ = "agents"
    
    id: str = SQLField(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    name: str
    model: str
    metadata: Dict[str, Any] = SQLField(default_factory=dict, sa_column=SQLField(JSON))
    
    # Relationships
    events: List["Event"] = Relationship(back_populates="agent")


def init_db():
    """Initialize the database."""
    SQLModel.metadata.create_all(engine)
