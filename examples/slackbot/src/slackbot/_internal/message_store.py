"""Durable per-thread storage for pydantic-ai `ModelMessage` history.

The bot used to persist conversation history in a SQLite file on the
container's local disk. On Cloud Run that disk is ephemeral — every revision
deploy wiped the history, and ad-hoc retrieval ("what did marvin actually say
in thread X?") required shelling into a running container.

This module replaces that with a `WritableFileSystem`-backed store. Each
thread's full `ModelMessage` list lives in a single JSON object keyed by
thread_ts. Writes overwrite the whole object, protected by an in-process
per-thread `asyncio.Lock` to keep concurrent turns in the same thread from
clobbering each other (the bot is currently single-instance, so an in-process
lock is sufficient — if we move to multiple replicas this needs to become a
distributed lock or compare-and-swap, but that's not today's problem).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from pathlib import Path

from prefect.blocks.core import Block
from prefect.filesystems import LocalFileSystem, WritableFileSystem
from prefect.logging.loggers import get_logger
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

logger = get_logger(__name__)


async def load_message_store(block_slug: str | None, local_dir: Path) -> "MessageStore":
    """Construct a `MessageStore` from settings.

    If `block_slug` is set, load that `WritableFileSystem` block from the
    Prefect workspace (e.g. `gcs-bucket/marvin-chat-history` in prod/stg).
    Otherwise fall back to a `LocalFileSystem` rooted at `local_dir` — fine
    for local dev, not durable in Cloud Run.
    """
    if block_slug:
        block = await Block.aload(block_slug)
        if not isinstance(block, WritableFileSystem):
            raise TypeError(
                f"Block {block_slug!r} is not a WritableFileSystem "
                f"(got {type(block).__name__})"
            )
        logger.info("Using message store block %s", block_slug)
        return MessageStore(block)

    local_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Using local message store at %s", local_dir)
    return MessageStore(LocalFileSystem(basepath=str(local_dir)))


def _thread_key(thread_ts: str) -> str:
    return f"threads/{thread_ts}.json"


class MessageStore:
    """A thin per-thread message archive over a `WritableFileSystem` block."""

    def __init__(self, fs: WritableFileSystem) -> None:
        self._fs = fs
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def get(self, thread_ts: str) -> list[ModelMessage]:
        """Return the full message history for a thread, or [] if none stored."""
        try:
            data = await self._fs.aread_path(_thread_key(thread_ts))  # type: ignore[attr-defined]
        except (FileNotFoundError, ValueError):
            # LocalFileSystem raises ValueError("Path ... does not exist."),
            # cloud impls typically raise FileNotFoundError. Treat both as "empty".
            return []
        except Exception:
            logger.exception("Failed to read message history for thread %s", thread_ts)
            raise
        if not data:
            return []
        return list(ModelMessagesTypeAdapter.validate_json(data))

    async def append(
        self, thread_ts: str, new_messages: list[ModelMessage]
    ) -> list[ModelMessage]:
        """Append `new_messages` to the thread's history and return the full list.

        Read-modify-write under a per-thread lock so two overlapping turns
        in the same thread don't clobber each other.
        """
        if not new_messages:
            return await self.get(thread_ts)

        async with self._locks[thread_ts]:
            existing = await self.get(thread_ts)
            combined = existing + list(new_messages)
            dumped = ModelMessagesTypeAdapter.dump_json(combined)
            await self._fs.awrite_path(_thread_key(thread_ts), dumped)  # type: ignore[attr-defined]
            return combined
