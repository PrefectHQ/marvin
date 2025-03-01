"""Test configuration and fixtures."""

import threading
from pathlib import Path
from tempfile import TemporaryDirectory

import chromadb
import pytest

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
    with TemporaryDirectory() as temp_dir:
        original_path = settings.database_url

        # Create unique path per worker to avoid conflicts
        worker_suffix = worker_id if worker_id != "master" else ""
        temp_path = Path(temp_dir) / f"test{worker_suffix}.db"
        database_url = f"sqlite+aiosqlite:///{temp_path}"

        with _db_lock:
            # Configure database settings
            monkeypatch.setattr(settings, "database_url", database_url)

            database._async_engine_cache.clear()

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

        settings.database_url = original_path
        # Clear engine cache
        database._async_engine_cache.clear()


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
def unit_test_instructions():
    with instructions(
        """
        You are being unit tested. Be as fast and concise as possible. Do not
        post unecessary messages.
        """
    ):
        yield
