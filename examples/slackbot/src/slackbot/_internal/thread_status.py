"""Thread status tracking for Slack events (cross-process safe).

This module encapsulates a tiny SQLite-backed status mechanism to avoid duplicate
processing of the same Slack thread when users edit their original post or when
Slack delivers multiple events. It keeps the rest of the app simple and avoids
sprawling status logic across files.
"""

from __future__ import annotations

from typing import Literal

from slackbot.core import Database

Status = Literal["in_progress", "completed"]


async def ensure_schema(db: Database) -> None:
    """Ensure the status table exists.

    Using CREATE TABLE IF NOT EXISTS is idempotent and cheap enough to call
    whenever we touch the status table, avoiding module-level state or locks.
    """

    def _create() -> None:
        db.con.execute(
            """
            CREATE TABLE IF NOT EXISTS slack_thread_status (
                thread_ts TEXT PRIMARY KEY,
                status TEXT NOT NULL CHECK (status IN ('in_progress','completed')),
                updated_at REAL NOT NULL
            );
            """
        )
        db.con.commit()

    await db.loop.run_in_executor(db.executor, _create)


async def try_acquire(db: Database, thread_ts: str) -> bool:
    """Attempt to mark a thread as in_progress; returns True if acquired.

    Uses an atomic INSERT OR IGNORE on a PRIMARY KEY to prevent duplicates across
    concurrent processes or tasks.
    """
    await ensure_schema(db)

    def _insert() -> int:
        cur = db.con.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO slack_thread_status (thread_ts, status, updated_at)
            VALUES (?, 'in_progress', strftime('%s','now'))
            """,
            (thread_ts,),
        )
        db.con.commit()
        return cur.rowcount

    rowcount: int = await db.loop.run_in_executor(db.executor, _insert)
    return rowcount == 1


async def get_status(db: Database, thread_ts: str) -> Status | None:
    await ensure_schema(db)

    def _query() -> Status | None:
        cur = db.con.cursor()
        cur.execute(
            "SELECT status FROM slack_thread_status WHERE thread_ts = ?",
            (thread_ts,),
        )
        row = cur.fetchone()
        return row[0] if row else None  # type: ignore[return-value]

    return await db.loop.run_in_executor(db.executor, _query)


async def mark_completed(db: Database, thread_ts: str) -> None:
    await ensure_schema(db)

    def _update() -> None:
        cur = db.con.cursor()
        cur.execute(
            """
            UPDATE slack_thread_status
            SET status = 'completed', updated_at = strftime('%s','now')
            WHERE thread_ts = ?
            """,
            (thread_ts,),
        )
        db.con.commit()

    await db.loop.run_in_executor(db.executor, _update)
