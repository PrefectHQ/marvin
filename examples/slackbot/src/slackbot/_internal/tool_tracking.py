"""Per-run tool call tracking for the answering agent.

A `ToolCallWatcher` belongs to one agent run. It is attached to that run as a
pydantic-ai `Hooks` capability, so concurrent Slack turns never share a tally,
a limit, or a progress message.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Protocol

from prefect import task
from pydantic_ai import RunContext
from pydantic_ai.capabilities import Hooks, WrapToolExecuteHandler
from pydantic_ai.exceptions import ToolFailed
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.tools import ToolDefinition

TOOL_LIMIT_MESSAGE = (
    "Tool use limit reached. Please continue with the information "
    "you've gathered so far to answer the user's question."
)


class Progress(Protocol):
    header: str

    async def update(self, text: str) -> Any: ...


@dataclass
class ToolCallWatcher:
    """Count, limit, and report the tool calls of a single agent run.

    Each allowed call runs as a Prefect task and updates the progress message.
    Calls past `max_tool_calls` are not executed: the model receives a failed
    tool result telling it to answer with what it has.
    """

    max_tool_calls: int = 50
    progress: Progress | None = None
    task_settings: dict[str, Any] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def capability(self) -> Hooks[Any]:
        """The capability to pass to `agent.run(capabilities=[...])`."""
        return Hooks(tool_execute=self._execute)

    async def _execute(
        self,
        ctx: RunContext[Any],
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: dict[str, Any],
        handler: WrapToolExecuteHandler,
    ) -> Any:
        tool_name = call.tool_name
        if sum(self.counts.values()) >= self.max_tool_calls:
            raise ToolFailed(TOOL_LIMIT_MESSAGE)
        self.counts[tool_name] += 1
        await self._update_progress(tool_name)

        async def execute_tool(args: dict[str, Any]) -> Any:
            return await handler(args)

        settings = dict(self.task_settings)
        if run_name := settings.get("task_run_name"):
            settings["task_run_name"] = run_name.replace("{tool_name}", tool_name)
        return await task(**settings)(execute_tool)(args)

    async def _update_progress(self, tool_name: str) -> None:
        if self.progress is None:
            return
        lines = [
            self.progress.header,
            "",
            "",
            f"🔧 Using tool: `{tool_name}`",
            "",
            "📊 Tools used:",
            *(
                f"  • `{tool}` ({count}x)"
                for tool, count in sorted(self.counts.items())
            ),
        ]
        try:
            await self.progress.update("\n".join(lines))
        except Exception:
            # a failed progress edit must never fail the tool call
            pass
