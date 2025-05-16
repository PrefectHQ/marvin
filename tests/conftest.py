"""Test configuration and fixtures."""

import os
import threading
from pathlib import Path
from tempfile import TemporaryDirectory

import chromadb
import pytest
from pydantic_ai.models.test import TestModel

import marvin
from marvin import database, settings
from marvin.defaults import override_defaults
from marvin.instructions import instructions
from marvin.memory.providers.chroma import ChromaMemory

# Lock for database operations
_db_lock = threading.Lock()


@pytest.fixture(autouse=True)
async def setup_test_db(monkeypatch: pytest.MonkeyPatch, worker_id: str):
    """Use a temporary database for tests.

    The worker_id fixture is provided by pytest-xdist and will be 'gw0', 'gw1', etc
    for parallel test runners, or 'master' for single-process runs.
    """
    original_env_marvin_db_url = os.getenv("MARVIN_DATABASE_URL")
    original_settings_db_url = (
        str(settings.database_url) if settings.database_url else None
    )

    with TemporaryDirectory() as temp_dir_name:
        temp_path = Path(temp_dir_name) / f"test_marvin_{worker_id}.db"
        test_db_url = f"sqlite+aiosqlite:///{temp_path}"  # Ensure async URL for tests

        with _db_lock:
            # Set MARVIN_DATABASE_URL env var for the test's scope.
            # This ensures the validator in Settings picks up this test-specific URL.
            monkeypatch.setenv("MARVIN_DATABASE_URL", test_db_url)

            # Clear cached engines for the new URL.
            database._async_engine_cache.clear()

            # Force re-evaluation of settings.database_url to use the new env var.
            # Direct assignment triggers the 'before' validator due to `validate_assignment=True`.
            if hasattr(settings, "database_url"):
                monkeypatch.setattr(settings, "database_url", test_db_url)
            else:
                # Fallback, though direct setattr is expected to work.
                settings.database_url = test_db_url

            # Verify the global settings object reflects the test_db_url.
            assert str(settings.database_url) == test_db_url, (
                f"Failed to set database_url for test. Expected {test_db_url}, got {settings.database_url}"
            )

            # create_db_and_tables with force=True ensures a clean slate.
            await database.create_db_and_tables(force=True)

        yield

        # Teardown
        with _db_lock:
            database._async_engine_cache.clear()

            # Restore original MARVIN_DATABASE_URL environment variable.
            if original_env_marvin_db_url is not None:
                monkeypatch.setenv("MARVIN_DATABASE_URL", original_env_marvin_db_url)
            else:
                monkeypatch.delenv("MARVIN_DATABASE_URL", raising=False)

            # Restore original database_url on the global settings object.
            # The validator will run, using the (restored or absent) MARVIN_DATABASE_URL.
            if hasattr(settings, "database_url"):
                monkeypatch.setattr(
                    settings,
                    "database_url",
                    original_settings_db_url
                    if original_settings_db_url is not None
                    else None,
                )
            else:
                settings.database_url = (
                    original_settings_db_url
                    if original_settings_db_url is not None
                    else None
                )


@pytest.fixture
async def session():
    """Provide an async database session for tests."""
    async with database.get_async_session() as session:
        yield session


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


@pytest.fixture
def gpt_4o_audio_preview():
    with override_defaults(model="openai:gpt-4o-audio-preview"):
        yield


@pytest.fixture(autouse=True)
def restore_defaults():
    """
    Ensure that the defaults are restored after each test, in case the test
    modified them.
    """
    with override_defaults(**marvin.defaults.__dict__):
        yield


@pytest.fixture
def unit_test_instructions():
    with instructions(
        """
        You are being unit tested. Be as fast and concise as possible. Do not
        post unecessary messages.
        """
    ):
        yield


@pytest.fixture()
def test_model():
    model = TestModel()
    with override_defaults(model=model):
        yield model
