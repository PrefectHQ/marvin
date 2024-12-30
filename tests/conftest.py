"""Test configuration and fixtures."""

import pytest
from pathlib import Path
from sqlmodel import create_engine, SQLModel
from tempfile import TemporaryDirectory

from marvin import settings
from marvin.engine import database


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
