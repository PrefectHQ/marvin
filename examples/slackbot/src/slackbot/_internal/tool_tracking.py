"""Tool usage tracking and limiting for pydantic-ai agents."""

from collections import defaultdict
from contextvars import ContextVar
from typing import Any

# Context variables for tracking tool usage
tool_usage_counts: ContextVar[dict[str, int] | None] = ContextVar(
    "tool_usage_counts", default=None
)
current_tool: ContextVar[str | None] = ContextVar("current_tool", default=None)
progress_message: ContextVar[Any] = ContextVar("progress_message", default=None)


class ToolUsageTracker:
    """Tracks and limits tool usage for agents."""

    def __init__(self, max_calls: int = 50):
        self.max_calls = max_calls

    def track_call(self, tool_name: str) -> str | None:
        """Track a tool call and return error message if limit exceeded.

        Args:
            tool_name: Name of the tool being called

        Returns:
            Error message if limit exceeded, None otherwise
        """
        counts = tool_usage_counts.get()
        if counts is None:
            counts = defaultdict(int)
            tool_usage_counts.set(counts)

        counts[tool_name] += 1
        total_calls = sum(counts.values())

        if total_calls > self.max_calls:
            return (
                "Tool use limit reached. Please continue with the information "
                "you've gathered so far to answer the user's question."
            )
        return None

    def get_counts(self) -> dict[str, int]:
        """Get current tool usage counts."""
        counts = tool_usage_counts.get()
        return dict(counts) if counts else {}

    async def update_progress(self, tool_name: str):
        """Update progress message if available."""
        progress = progress_message.get()
        if not progress:
            return

        token = current_tool.set(tool_name)
        try:
            counts = self.get_counts()
            lines = [f"🔧 Using: `{tool_name}`", ""]

            if counts:
                lines.append("📊 Tools used:")
                for tool, count in sorted(counts.items()):
                    lines.append(f"  • `{tool}` ({count}x)")

            await progress.update("\n".join(lines))
        except Exception:
            pass
        finally:
            current_tool.reset(token)
