"""Test configuration and fixtures."""

import sqlite3
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import chromadb
import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

import marvin
from marvin import settings
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

            # Patch the engine creation to use NullPool
            original_create_engine = database.create_engine

            def patched_create_engine(*args: Any, **kwargs: Any) -> Engine:
                kwargs["poolclass"] = NullPool
                return original_create_engine(*args, **kwargs)

            monkeypatch.setattr(database, "create_engine", patched_create_engine)

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


@pytest.fixture(autouse=True)
def setup_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        marvin.defaults,
        "memory_provider",
        ChromaMemory(
            client=chromadb.PersistentClient(path=str(tmp_path / "controlflow-memory")),
        ),
    )
