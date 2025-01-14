"""Test configuration and fixtures."""

import sqlite3
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import chromadb
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

import marvin
from marvin import settings
from marvin.defaults import override_defaults
from marvin.engine import database
from marvin.memory.providers.chroma import ChromaMemory


# Configure SQLite to use WAL mode for better concurrency
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(
    dbapi_connection: sqlite3.Connection,
    connection_record: Any,
) -> None:
    """Configure SQLite connection for better concurrency.

    Args:
        dbapi_connection: The SQLite connection
        connection_record: SQLAlchemy connection record (unused)

    """
    cursor = dbapi_connection.cursor()
    # Use WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")
    # Reduce durability guarantees for testing
    cursor.execute("PRAGMA synchronous=OFF")
    # Increase timeout for busy connections
    cursor.execute("PRAGMA busy_timeout=10000")  # 10 second timeout
    # Aggressive cache settings for testing
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()


# Lock for database operations
_db_lock = threading.Lock()


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch: pytest.MonkeyPatch, worker_id: str):
    """Use a temporary database for tests.

    The worker_id fixture is provided by pytest-xdist and will be 'gw0', 'gw1', etc
    for parallel test runners, or 'master' for single-process runs.
    """
    with TemporaryDirectory() as temp_dir:
        original_path = settings.database_path

        # Create unique path per worker to avoid conflicts
        worker_suffix = worker_id if worker_id != "master" else ""
        temp_path = Path(temp_dir) / f"test{worker_suffix}.db"

        with _db_lock:
            # Configure database settings
            monkeypatch.setattr(settings, "database_path", temp_path)

            # Create engines with NullPool
            sync_engine = create_engine(
                f"sqlite:///{temp_path}",
                echo=False,
                connect_args={"check_same_thread": False},
                poolclass=NullPool,
            )
            async_engine = create_async_engine(
                f"sqlite+aiosqlite:///{temp_path}",
                echo=False,
                connect_args={"check_same_thread": False},
                poolclass=NullPool,
            )

            # Set the engines
            database.set_engine(sync_engine)
            database.set_async_engine(async_engine)

            # Create tables with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    database.create_db_and_tables(force=True)
                    break
                except Exception:
                    if attempt == max_retries - 1:
                        raise
                    continue

        yield

        settings.database_path = original_path
        # Clear engine cache
        database._engine_cache.clear()
        database._async_engine_cache.clear()


@pytest.fixture(autouse=True)
def setup_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, worker_id: str):
    monkeypatch.setattr(
        marvin.defaults,
        "memory_provider",
        ChromaMemory(
            client=chromadb.PersistentClient(
                path=str(tmp_path / "controlflow-memory" / worker_id)
            ),
        ),
    )


@pytest.fixture
def gpt_4o():
    with override_defaults(model="openai:gpt-4o"):
        yield
