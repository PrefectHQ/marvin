import datetime
from dataclasses import dataclass
from typing import Any, get_origin

import rich
from rich import box
from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.pretty import Pretty
from rich.spinner import Spinner
from rich.table import Table

from marvin.engine.end_turn import (
    DelegateToAgent,
    EndTurn,
    MarkTaskFailed,
    MarkTaskSkipped,
    MarkTaskSuccessful,
    PostMessage,
)
from marvin.engine.events import (
    AgentMessageEvent,
    OrchestratorEndEvent,
    OrchestratorExceptionEvent,
    OrchestratorStartEvent,
    ToolCallEvent,
    ToolRetryEvent,
    ToolReturnEvent,
)
from marvin.engine.handlers import Handler
from marvin.utilities.types import issubclass_safe

# Global spinner for consistent animation
RUNNING_SPINNER = Spinner("dots")


@dataclass(kw_only=True)
class DisplayState:
    """Base class for content to be displayed."""

    agent_name: str
    first_timestamp: datetime.datetime

    def format_timestamp(self) -> str:
        """Format the timestamp for display."""
        local_timestamp = self.first_timestamp.astimezone()
        return local_timestamp.strftime("%I:%M:%S %p").lstrip("0").rjust(11)


@dataclass(kw_only=True)
class ContentState(DisplayState):
    """State for content being streamed."""

    content: str = ""

    @staticmethod
    def _convert_content_to_str(content: Any) -> str:
        """Convert various content formats to a string."""
        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            return content.get("content", content.get("text", ""))

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    part = item.get("content", item.get("text", ""))
                    if part:
                        parts.append(part)
            return "\n".join(parts)

        return str(content)

    def update_content(self, new_content: Any) -> None:
        """Update content, converting complex content types to string."""
        self.content = self._convert_content_to_str(new_content)

    def render_panel(self) -> Panel:
        """Render content as a markdown panel."""
        return Panel(
            Markdown(self.content),
            title=f"[bold]{self.agent_name}[/]",
            subtitle=f"[italic]{self.format_timestamp()}[/]",
            title_align="left",
            subtitle_align="right",
            border_style="blue",
            box=box.ROUNDED,
            width=100,
            padding=(1, 2),
        )


@dataclass(kw_only=True)
class ToolState(DisplayState):
    """State for a tool call and its result."""

    name: str
    args: dict[str, Any]
    result: str | None = None
    is_error: bool = False
    is_complete: bool = False
    end_turn_tool: EndTurn | None = None

    def get_status_style(self) -> tuple[str | Spinner, str, str]:
        """Returns (icon, text style, border style) for current status."""
        if self.is_complete:
            if self.is_error:
                return "❌", "red", "red"
            return "✅", "green", "green"  # Slightly softer green

        return (RUNNING_SPINNER, "yellow", "gray50")  # Use shared spinner instance

    def render_panel(self) -> Panel:
        """Render tool state as a panel with status indicator."""
        icon, text_style, border_style = self.get_status_style()

        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim")
        table.add_column()

        name = self.name
        if self.end_turn_tool:
            if issubclass_safe(get_origin(self.end_turn_tool), MarkTaskSuccessful):
                name = f"Mark Task Successful: {self.end_turn_tool.task_id}"
            elif issubclass_safe(self.end_turn_tool, MarkTaskFailed):
                name = f"Mark Task Failed: {self.end_turn_tool.task_id}"
            elif issubclass_safe(self.end_turn_tool, MarkTaskSkipped):
                name = f"Mark Task Skipped: {self.end_turn_tool.task_id}"
            elif issubclass_safe(self.end_turn_tool, PostMessage):
                name = "Post Message"
            elif issubclass_safe(self.end_turn_tool, DelegateToAgent):
                name = "Delegate to Agent"
            else:
                name = self.end_turn_tool.__name__
        table.add_row("Tool:", f"[{text_style} bold]{name}[/]")

        if self.args:
            if self.end_turn_tool:
                args = self.args.get("response", self.args)
                if issubclass_safe(get_origin(self.end_turn_tool), MarkTaskSuccessful):
                    args = args.get("result", args)
            else:
                args = self.args

            table.add_row("Input:", Markdown(str(args)))

        table.add_row("Status:", icon)
        if self.is_complete and self.result and not self.end_turn_tool:
            label = "Error" if self.is_error else "Output"
            output = f"[red]{self.result}[/]" if self.is_error else Pretty(self.result)
            table.add_row(f"{label}:", output)

        return Panel(
            table,
            title=f"[bold]{self.agent_name}[/]",
            subtitle=f"[italic]{self.format_timestamp()}[/]",
            title_align="left",
            subtitle_align="right",
            border_style=border_style,
            box=box.ROUNDED,
            width=100,
            padding=(0, 1),
        )


class PrintHandler(Handler):
    """A handler that prints events to the console in a rich, interactive format."""

    def __init__(self):
        self.live: Live | None = None
        self.states: dict[str, DisplayState] = {}
        self.paused_id: str | None = None

    def update_display(self):
        """Render all current state as panels and update display."""
        if not self.live or not self.live.is_started:
            return

        sorted_states = sorted(self.states.values(), key=lambda s: s.first_timestamp)
        panels: list[Panel] = []

        for state in sorted_states:
            panels.append(state.render_panel())

        if panels:
            self.live.update(Group(*panels), refresh=True)

    def on_orchestrator_start(self, event: OrchestratorStartEvent):
        """Initialize live display when orchestrator starts."""
        if not self.live:
            self.live = Live(vertical_overflow="visible", auto_refresh=True)
            try:
                self.live.start()
            except rich.errors.LiveError:
                pass

    def on_orchestrator_end(self, event: OrchestratorEndEvent):
        """Clean up live display when orchestrator ends."""
        if self.live and self.live.is_started:
            try:
                self.live.stop()
            except rich.errors.LiveError:
                pass
            self.live = None
            self.states.clear()

    def on_orchestrator_exception(self, event: OrchestratorExceptionEvent):
        """Clean up live display when orchestrator encounters an error."""
        if self.live and self.live.is_started:
            try:
                self.live.stop()
            except rich.errors.LiveError:
                pass
            self.live = None
            self.states.clear()

    def on_agent_message(self, event: AgentMessageEvent):
        """Handle agent message events by updating content state."""
        if not event.message.content:
            return

        if str(event.id) not in self.states:
            state = ContentState(
                agent_name=event.agent.name,
                first_timestamp=event.timestamp,
            )
            state.update_content(event.message.content)
            self.states[str(event.id)] = state
        else:
            state = self.states[str(event.id)]
            if isinstance(state, ContentState):
                state.update_content(event.message.content)

        self.update_display()

    def on_tool_call(self, event: ToolCallEvent):
        """Handle tool call events by updating tool state."""
        tool_id = event.message.tool_call_id
        if not self.paused_id and event.message.tool_name == "cli":
            self.paused_id = tool_id
            if self.live and self.live.is_started:
                self.live.stop()
            return

        if tool_id not in self.states:
            self.states[tool_id] = ToolState(
                agent_name=event.agent.name,
                first_timestamp=event.timestamp,
                name=event.message.tool_name,
                args=event.message.args_as_dict(),
                end_turn_tool=event.end_turn_tool,
            )
        else:
            state = self.states[tool_id]
            if isinstance(state, ToolState):
                state.args = event.message.args_as_dict()

        self.update_display()

    def on_tool_return(self, event: ToolReturnEvent):
        """Handle tool return events by updating tool state."""
        tool_id = event.message.tool_call_id

        if event.message.tool_name == "cli":
            if self.paused_id == tool_id:
                self.paused_id = None

                self.live = Live(vertical_overflow="visible", auto_refresh=True)
                self.live.start()
            return

        if tool_id in self.states:
            state = self.states[tool_id]
            if isinstance(state, ToolState):
                state.is_complete = True
                state.result = event.message.content

        self.update_display()

    def on_tool_retry(self, event: ToolRetryEvent):
        """Handle tool retry events by updating tool state."""
        tool_id = event.message.tool_call_id
        if tool_id in self.states:
            state = self.states[tool_id]
            if isinstance(state, ToolState):
                state.is_complete = True
                state.is_error = True
                state.result = event.message.content

        self.update_display()
