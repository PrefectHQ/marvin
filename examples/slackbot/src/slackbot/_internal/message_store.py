"""Durable per-thread storage for pydantic-ai `ModelMessage` history.

The bot used to persist conversation history in a SQLite file on the
container's local disk. On Cloud Run that disk is ephemeral — every revision
deploy wiped the history, and ad-hoc retrieval ("what did marvin actually say
in thread X?") required shelling into a running container.

This module replaces that with a `WritableFileSystem`-backed store. Each
thread's full `ModelMessage` list lives in a single JSON object keyed by
thread_ts. Writes overwrite the whole object, protected by an in-process
lock that guards the read-modify-write — see `MessageStore.append`.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from prefect.blocks.core import Block
from prefect.filesystems import LocalFileSystem, WritableFileSystem
from prefect.logging.loggers import get_logger
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

logger = get_logger(__name__)

# Backends raise their own "not found" exception types — collect them so
# `MessageStore.get` can treat a missing thread uniformly as []. Imported
# defensively so this module doesn't hard-require any particular backend.
_NOT_FOUND_EXCEPTIONS: tuple[type[BaseException], ...] = (FileNotFoundError,)
try:
    from google.api_core.exceptions import NotFound as _GcsNotFound

    _NOT_FOUND_EXCEPTIONS = (*_NOT_FOUND_EXCEPTIONS, _GcsNotFound)
except ImportError:
    pass

# Slack thread_ts is always `<seconds>.<microseconds>`, e.g. "1778543248.702039".
# We use it directly as a filesystem path key — validate strictly so a caller
# can't supply `../...` or absolute paths and influence what the store
# reads/writes. The `/chat` endpoint does not verify Slack signatures, so
# treating thread_ts as untrusted input is the right default.
_THREAD_TS_RE = re.compile(r"^\d+\.\d+$")


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
    if not _THREAD_TS_RE.match(thread_ts):
        raise ValueError(f"invalid thread_ts: {thread_ts!r}")
    return f"threads/{thread_ts}.json"


class MessageStore:
    """A thin per-thread message archive over a `WritableFileSystem` block.

    A single asyncio lock guards all read-modify-write transactions. With
    the bot's traffic profile (low QPS, single Cloud Run instance) the
    serialization cost is negligible, and it sidesteps the unbounded
    per-thread lock dict that a finer-grained scheme would require. If
    we ever go multi-replica or hit real contention, this becomes a
    distributed primitive (CAS or external lock).
    """

    def __init__(self, fs: WritableFileSystem) -> None:
        self._fs = fs
        self._write_lock = asyncio.Lock()

    async def get(self, thread_ts: str) -> list[ModelMessage]:
        """Return the full message history for a thread, or [] if none stored."""
        key = _thread_key(thread_ts)
        try:
            data = await self._fs.aread_path(key)  # type: ignore[attr-defined]
        except _NOT_FOUND_EXCEPTIONS:
            return []
        except ValueError as e:
            # LocalFileSystem signals missing files with `ValueError("Path ...
            # does not exist.")`. Match only that case; re-raise anything else
            # (e.g. "Path ... is not a file") so real failures don't get
            # silently swallowed as empty history.
            if "does not exist" in str(e):
                return []
            raise
        if not data:
            return []
        return list(ModelMessagesTypeAdapter.validate_json(data))

    async def append(
        self, thread_ts: str, new_messages: list[ModelMessage]
    ) -> list[ModelMessage]:
        """Append `new_messages` to the thread's history and return the full list.

        Read-modify-write under `self._write_lock` so two overlapping turns
        don't clobber each other's writes.
        """
        if not new_messages:
            return await self.get(thread_ts)

        async with self._write_lock:
            existing = await self.get(thread_ts)
            combined = existing + list(new_messages)
            dumped = ModelMessagesTypeAdapter.dump_json(combined)
            await self._fs.awrite_path(_thread_key(thread_ts), dumped)  # type: ignore[attr-defined]
            return combined
