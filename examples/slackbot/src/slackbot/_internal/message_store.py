"""Durable per-thread storage for pydantic-ai `ModelMessage` history.

Conversation history lives in the Prefect workspace as block documents —
one per thread, named `chat-history-<sanitized_thread_ts>`. The bot
already authenticates to the workspace, so this needs no extra infra
(no bucket, no service account grant, no env-var dance).

Why block documents (not Variables, not artifacts, not files):

- Variables cap at 5000 chars per value — a single agent turn with tool
  calls blows that.
- Artifacts are version-chained on each `create_*_artifact(key=...)`
  call, so they don't naturally support "overwrite latest" semantics
  and accumulate records per turn.
- Block documents store arbitrary JSON in their `data` column (no
  practical size limit for our use case), support atomic upserts via
  `block.save(name, overwrite=True)`, and are looked up by name in O(1).

Reads use `ChatHistoryBlock.aload(name)` which raises `ValueError` on
miss — the natural empty-thread path. Writes are guarded by a single
in-process `asyncio.Lock` to keep concurrent turns from clobbering each
other's read-modify-write (the bot is single-instance on Cloud Run; if
we go multi-replica this needs a distributed primitive).
"""

from __future__ import annotations

import asyncio
import re

from prefect.blocks.core import Block
from prefect.logging.loggers import get_logger
from pydantic import Field
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

logger = get_logger(__name__)

# Slack thread_ts is always `<seconds>.<microseconds>`, e.g. "1778543248.702039".
# Validate strictly so a caller can't supply arbitrary characters — the value
# becomes part of a Prefect block-document name and Slack signature
# verification isn't in place on the `/chat` endpoint.
_THREAD_TS_RE = re.compile(r"^\d+\.\d+$")


class ChatHistoryBlock(Block):
    """Per-thread chat history as a Prefect block document.

    The `messages_json` field holds the full `ModelMessage[]` serialized
    by `pydantic_ai.messages.ModelMessagesTypeAdapter`. We keep it as a
    string (rather than a structured field) so the block schema doesn't
    have to track every pydantic-ai message variant.
    """

    _block_type_name = "Chat History"
    _logo_url = "https://avatars.githubusercontent.com/u/39270919"  # PrefectHQ

    messages_json: str = Field(
        default="[]",
        description="pydantic-ai ModelMessage[] serialized via ModelMessagesTypeAdapter",
    )


def _block_name(thread_ts: str) -> str:
    if not _THREAD_TS_RE.match(thread_ts):
        raise ValueError(f"invalid thread_ts: {thread_ts!r}")
    # Block document names must be alphanumeric + dashes only — replace `.`
    # with `-` to keep round-tripping unambiguous.
    return f"chat-history-{thread_ts.replace('.', '-')}"


class MessageStore:
    """Per-thread message archive over Prefect `ChatHistoryBlock` documents.

    A single store-wide `asyncio.Lock` guards all read-modify-write
    transactions. Bot traffic is low enough that the serialization is
    free; if we ever go multi-replica this becomes a distributed
    primitive (CAS or external lock).
    """

    def __init__(self) -> None:
        self._write_lock = asyncio.Lock()

    async def get(self, thread_ts: str) -> list[ModelMessage]:
        """Return the full message history for a thread, or [] if none stored."""
        name = _block_name(thread_ts)
        try:
            block = await ChatHistoryBlock.aload(name)
        except ValueError:
            # Block.aload raises ValueError when the document doesn't exist.
            # That's the empty-thread case — any other ValueError shape would
            # be unexpected and is fine to propagate.
            return []
        if not block.messages_json:
            return []
        return list(ModelMessagesTypeAdapter.validate_json(block.messages_json))

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
            dumped = ModelMessagesTypeAdapter.dump_json(combined).decode()
            block = ChatHistoryBlock(messages_json=dumped)
            await block.save(_block_name(thread_ts), overwrite=True)
            return combined
