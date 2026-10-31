"""Regression: a schema created by the runtime must be stamped at Alembic head.

Importing ``marvin`` creates the SQLite tables directly from the models
(``Base.metadata.create_all``), which left ``alembic_version`` empty. The
documented ``marvin db upgrade`` then failed on the initial revision with
``sqlite3.OperationalError: table threads already exists``, and because that
revision never completed, no later migration could ever be applied either.
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory

from marvin import database, settings
from marvin.cli.migrations import get_alembic_cfg


def _test_db_path() -> Path:
    url = str(settings.database_url)
    assert url.startswith("sqlite"), url
    return Path(url.split("///", 1)[1])


def _head_revision() -> str:
    return ScriptDirectory.from_config(get_alembic_cfg()).get_current_head()


async def test_runtime_created_schema_is_stamped_at_head():
    """The tables were created by the runtime, so the revision must be recorded."""
    with sqlite3.connect(_test_db_path()) as conn:
        rows = list(conn.execute("select version_num from alembic_version"))

    assert rows == [(_head_revision(),)]


async def test_upgrade_after_runtime_creation_succeeds():
    """``marvin db upgrade`` must not try to re-create existing tables.

    Alembic runs its own event loop, so the command is executed in a worker
    thread where no loop is running.
    """
    await asyncio.to_thread(command.upgrade, get_alembic_cfg(), "head")

    with sqlite3.connect(_test_db_path()) as conn:
        rows = list(conn.execute("select version_num from alembic_version"))

    assert rows == [(_head_revision(),)]


async def test_existing_unstamped_database_is_stamped():
    """A database created before the stamp existed gets one on the next use."""
    db_path = _test_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute("drop table alembic_version")

    await database.create_db_and_tables()

    with sqlite3.connect(db_path) as conn:
        rows = list(conn.execute("select version_num from alembic_version"))

    assert rows == [(_head_revision(),)]


async def test_drifted_database_is_not_stamped():
    """A schema that differs from the models is reported instead of stamped.

    Stamping it would record head for a schema that is not at head, which skips
    the migrations accounting for the difference.
    """
    db_path = _test_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute("alter table threads add column extra_col integer")
        conn.execute("drop table alembic_version")

    await database.create_db_and_tables()

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("select name from sqlite_master where type='table'")
        }

    assert "alembic_version" not in tables
