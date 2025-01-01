"""Test configuration and fixtures."""

from pathlib import Path
from tempfile import TemporaryDirectory

import chromadb
import pytest
from sqlmodel import SQLModel, create_engine

import marvin
from marvin import settings
from marvin.engine import database
from marvin.memory.providers.chroma import ChromaMemory


@pytest.fixture(autouse=True)
def setup_test_db():
    """Use a temporary database for tests."""
    with TemporaryDirectory() as temp_dir:
        # Store original values
        original_path = settings.database_path
        original_engine = database._engine

        # Set up test database
        temp_path = Path(temp_dir) / "test.db"
        settings.database_path = temp_path
        database._engine = create_engine(f"sqlite:///{temp_path}", echo=False)

        # Create tables
        SQLModel.metadata.create_all(database._engine)

        yield

        # Clean up
        database._engine.dispose()
        database._engine = original_engine
        settings.database_path = original_path


@pytest.fixture(autouse=True)
def setup_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(
        marvin.defaults,
        "memory_provider",
        ChromaMemory(
            client=chromadb.PersistentClient(path=str(tmp_path / "controlflow-memory"))
        ),
    )

    yield
