"""Type definitions for slack search MCP responses."""

from pydantic import BaseModel, computed_field


class ThreadSummary(BaseModel):
    """A search result representing a Slack thread summary."""

    key: str
    name: str
    description: str
    preview: str = ""
    score: float | None = None  # similarity score for semantic search

    @computed_field
    @property
    def channel_id(self) -> str:
        """Extract channel ID from key."""
        # key format: slack://workspace/bot/BOT_ID/summary/CHANNEL_ID/THREAD_TS
        parts = self.key.split("/")
        if len(parts) >= 6:
            return parts[5]
        return ""

    @computed_field
    @property
    def thread_ts(self) -> str:
        """Extract thread timestamp from key."""
        parts = self.key.split("/")
        if len(parts) >= 7:
            return parts[6]
        return ""


class ThreadDetail(BaseModel):
    """Full thread details including metadata."""

    key: str
    name: str
    description: str
    last_seen: str
    metadata: dict

    @computed_field
    @property
    def title(self) -> str:
        """Thread title from metadata."""
        return self.metadata.get("title", self.name)

    @computed_field
    @property
    def summary(self) -> str:
        """Full summary text."""
        return self.metadata.get("summary", "")

    @computed_field
    @property
    def key_topics(self) -> list[str]:
        """Key topics discussed in the thread."""
        return self.metadata.get("key_topics", [])

    @computed_field
    @property
    def message_count(self) -> int:
        """Number of messages in the thread."""
        return self.metadata.get("message_count", 0)

    @computed_field
    @property
    def participant_count(self) -> int:
        """Number of participants in the thread."""
        return self.metadata.get("participant_count", 0)

    @computed_field
    @property
    def channel_id(self) -> str:
        """Slack channel ID."""
        return self.metadata.get("channel_id", "")

    @computed_field
    @property
    def thread_ts(self) -> str:
        """Thread timestamp."""
        return self.metadata.get("thread_ts", "")

    @computed_field
    @property
    def workspace(self) -> str:
        """Slack workspace name."""
        return self.metadata.get("workspace_name", "")


class Stats(BaseModel):
    """Index statistics."""

    total_threads: int
    with_embeddings: int
