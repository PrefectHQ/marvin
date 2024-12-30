"""
Database management for persistence.

This module provides utilities for managing database sessions and migrations.
"""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

from marvin.settings import settings


# Sync engine and session
_engine = create_engine(
    f"sqlite:///{settings.database_path}",
    echo=False,
    connect_args={"check_same_thread": False},
)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session."""
    session = Session(_engine)
    try:
        yield session
    finally:
        session.close()


# Async engine and session
_async_engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.database_path}",
    echo=False,
    connect_args={"check_same_thread": False},
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    session = AsyncSession(_async_engine)
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
        SQLModel.metadata.drop_all(_engine)
    SQLModel.metadata.create_all(_engine)
