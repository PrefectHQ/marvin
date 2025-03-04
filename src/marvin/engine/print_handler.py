"""A simplified print handler for rendering streaming events from the engine."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Tuple

import rich
from rich import box
from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.pretty import Pretty
from rich.spinner import Spinner
from rich.table import Table

import marvin
from marvin.engine.end_turn import (
    EndTurn,
    MarkTaskSuccessful,
)
from marvin.engine.events import (
    ActorMessageDeltaEvent,
    ActorMessageEvent,
    EndTurnToolCallEvent,
    EndTurnToolResultEvent,
    OrchestratorEndEvent,
    OrchestratorStartEvent,
    ToolCallDeltaEvent,
    ToolCallEvent,
    ToolResultEvent,
    ToolRetryEvent,
)
from marvin.engine.handlers import Handler
from marvin.utilities.types import issubclass_safe

# Global spinner for consistent animation
RUNNING_SPINNER = Spinner("dots")


@dataclass
class EventPanel:
    """Base class for panels that represent events."""

    id: str
    agent_name: str
    timestamp: str

    def render(self) -> Panel:
        """Render this event as a panel."""
        raise NotImplementedError()


@dataclass
class MessagePanel(EventPanel):
    """Panel for displaying agent messages with streaming updates."""

    content: str = ""

    def render(self) -> Panel:
        """Render the message as a markdown panel."""
        return Panel(
            Markdown(self.content),
            title=f"[bold]{self.agent_name}[/]",
            subtitle=f"[italic]{self.timestamp}[/]",
            title_align="left",
            subtitle_align="right",
            border_style="blue",
            box=box.ROUNDED,
            width=100,
            padding=(1, 2),
        )


@dataclass
class ToolCallPanel(EventPanel):
    """Panel for displaying tool calls with streaming updates."""

    tool_name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    is_complete: bool = False
    result: str = ""
    is_error: bool = False
    is_end_turn_tool: bool = False
    tool: EndTurn | Callable[..., Any] | None = None

    def __post_init__(self):
        if self.args is None:
            self.args = {}

    def get_status_style(self) -> Tuple[Any, str, str]:
        """Returns (icon, text style, border style) for current status."""
        if self.is_complete:
            if self.is_error:
                return "❌", "red", "red"
            return "✅", "green", "green"
        return (
            RUNNING_SPINNER,
            "yellow",
            "gray50",
        )  # Use the shared spinner instance for in-progress status

    def render(self) -> Panel:
        """Render the tool call as a panel."""
        icon, text_style, border_style = self.get_status_style()

        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim")
        table.add_column()

        table.add_row("Tool:", self.tool_name)

        table.add_row("Status:", icon)

        if self.args:
            args = self.args
            if self.is_end_turn_tool:
                caption = "Result"
                if issubclass_safe(self.tool, MarkTaskSuccessful):
                    args = self.args.get("result", None)

            else:
                caption = "Input"
                args = self.args
            if isinstance(args, str):
                args = Markdown(args)
            else:
                args = Pretty(args)
            table.add_row(caption, args)

        if self.is_complete and self.result:
            label = "Error" if self.is_error else "Output"
            output = f"[red]{self.result}[/]" if self.is_error else Pretty(self.result)
            table.add_row(f"{label}:", output)

        return Panel(
            table,
            title=f"[bold]{self.agent_name}[/]",
            subtitle=f"[italic]{self.timestamp}[/]",
            title_align="left",
            subtitle_align="right",
            border_style=border_style,
            box=box.ROUNDED,
            width=100,
            padding=(1, 2),
        )


class PrintHandler(Handler):
    """A handler that renders events with streaming updates."""

    def __init__(self, hide_end_turn_tools: bool | None = None):
        self.live = None
        self.panels: Dict[str, EventPanel] = {}
        self.paused = False

        if hide_end_turn_tools is None:
            hide_end_turn_tools = (
                marvin.settings.default_print_handler_hide_end_turn_tools
            )
        self.hide_end_turn_tools = hide_end_turn_tools

    def format_timestamp(self, ts) -> str:
        """Format timestamp for display."""
        local_ts = ts.astimezone()
        return local_ts.strftime("%I:%M:%S %p").lstrip("0").rjust(11)

    def update_display(self):
        """Update the terminal display with current panels."""
        if not self.live or not self.live.is_started or self.paused:
            return

        # Sort panels by their timestamp attribute and filter out hidden end turn tools
        sorted_panels = sorted(
            [
                p
                for p in self.panels.values()
                if not (
                    self.hide_end_turn_tools
                    and isinstance(p, ToolCallPanel)
                    and p.is_end_turn_tool
                )
            ],
            key=lambda p: p.timestamp,
        )
        rendered = [p.render() for p in sorted_panels]

        if not rendered:
            self.live.update(None, refresh=True)
        else:
            self.live.update(Group(*rendered), refresh=True)

    def on_orchestrator_start(self, event: OrchestratorStartEvent):
        """Start the live display when orchestrator starts."""
        if not self.live:
            self.live = Live(
                vertical_overflow="visible",
                auto_refresh=True,
                refresh_per_second=10,  # Higher refresh rate for smoother animations
            )
            try:
                self.live.start()
            except rich.errors.LiveError:
                pass

    def on_orchestrator_end(self, event: OrchestratorEndEvent):
        """Clean up when orchestrator ends."""
        if self.live and self.live.is_started:
            try:
                self.live.stop()
            except rich.errors.LiveError:
                pass
            self.live = None
            self.panels.clear()

    def on_actor_message_delta(self, event: ActorMessageDeltaEvent):
        """Handle streaming updates to agent messages."""
        # Skip if snapshot doesn't exist or has no content
        if (
            not hasattr(event, "snapshot")
            or not event.snapshot
            or not hasattr(event.snapshot, "content")
            or not event.snapshot.content
        ):
            return

        # Create a stable ID from actor ID and message index
        actor_id = str(event.actor.id)
        # Use the timestamp as part of the stable ID to handle multiple messages from same actor
        msg_time = event.timestamp.isoformat()
        event_id = f"{actor_id}_{msg_time}"

        # Create or update the panel
        if event_id not in self.panels:
            self.panels[event_id] = MessagePanel(
                id=event_id,
                agent_name=event.actor.name,
                timestamp=self.format_timestamp(event.timestamp),
                content=event.snapshot.content,
            )
        else:
            # Update existing panel with the snapshot content
            panel = self.panels[event_id]
            if isinstance(panel, MessagePanel):
                panel.content = event.snapshot.content

        # Update the display to show streaming changes
        self.update_display()

    def on_actor_message(self, event: ActorMessageEvent):
        """Handle complete agent messages."""
        if not event.message.content:
            return

        event_id = str(event.id)

        # Create or update the panel
        if event_id not in self.panels:
            self.panels[event_id] = MessagePanel(
                id=event_id,
                agent_name=event.actor.name,
                timestamp=self.format_timestamp(event.timestamp),
                content=event.message.content,
            )
        else:
            # Update existing panel
            panel = self.panels[event_id]
            if isinstance(panel, MessagePanel):
                panel.content = event.message.content

        self.update_display()

    def on_tool_call_delta(self, event: ToolCallDeltaEvent):
        """Handle streaming updates to tool calls."""
        # Use snapshot.tool_call_id for consistency across deltas
        if not hasattr(event, "snapshot") or not event.snapshot:
            return

        tool_id = event.snapshot.tool_call_id
        if not tool_id:
            return

        # Handle CLI tools specially
        if event.snapshot.tool_name == "cli":
            self.paused = True
            if self.live and self.live.is_started:
                self.live.stop()
            return

        # Create or update the panel
        if tool_id not in self.panels:
            self.panels[tool_id] = ToolCallPanel(
                id=tool_id,
                agent_name=event.actor.friendly_name(),
                timestamp=self.format_timestamp(event.timestamp),
                tool_name=event.snapshot.tool_name,
                args=event.args_dict(),
                tool=event.tool,
            )
        else:
            # Update existing panel
            panel = self.panels[tool_id]
            if isinstance(panel, ToolCallPanel):
                panel.args = event.args_dict()

        # Always update to show streaming changes
        self.update_display()

    def on_tool_call(self, event: ToolCallEvent):
        """Handle complete tool calls."""
        tool_id = event.message.tool_call_id

        # Handle CLI tools specially
        if event.message.tool_name == "cli":
            self.paused = True
            if self.live and self.live.is_started:
                self.live.stop()
            return

        # Create or update the panel
        if tool_id not in self.panels:
            self.panels[tool_id] = ToolCallPanel(
                id=tool_id,
                agent_name=event.actor.friendly_name(),
                timestamp=self.format_timestamp(event.timestamp),
                tool_name=event.message.tool_name,
                args=event.args_dict(),
                tool=event.tool,
            )
        else:
            # Update existing panel
            panel = self.panels[tool_id]
            if isinstance(panel, ToolCallPanel):
                panel.args = event.args_dict()

        self.update_display()

    def on_tool_result(self, event: ToolResultEvent):
        """Handle tool result events."""
        tool_id = event.message.tool_call_id

        # Handle CLI tools specially
        if event.message.tool_name == "cli":
            if self.paused:
                self.paused = False
                self.live = Live(vertical_overflow="visible", auto_refresh=True)
                self.live.start()
            return

        # Update the tool call panel with results
        if tool_id in self.panels:
            panel = self.panels[tool_id]
            if isinstance(panel, ToolCallPanel):
                panel.is_complete = True
                panel.result = event.message.content

        self.update_display()

    def on_end_turn_tool_call(self, event: EndTurnToolCallEvent):
        """Handle end turn tool call events."""
        # Find the corresponding tool call panel and mark it as an end turn tool
        if event.tool_call_id in self.panels:
            panel: ToolCallPanel = self.panels[event.tool_call_id]
            panel.is_end_turn_tool = True
            if event.tool and event.tool.name is not None:
                panel.tool_name = event.tool.name
                panel.tool = event.tool
        else:
            self.panels[event.tool_call_id] = ToolCallPanel(
                id=event.tool_call_id,
                agent_name=event.actor.friendly_name(),
                timestamp=self.format_timestamp(event.timestamp),
                tool_name=event.tool.name,
                tool=event.tool,
            )
        self.update_display()

    def on_end_turn_tool_result(self, event: EndTurnToolResultEvent):
        if event.tool_call_id in self.panels:
            panel = self.panels[event.tool_call_id]
            if isinstance(panel, ToolCallPanel):
                panel.is_complete = True
                # the data is the fully-hydrated EndTurn class, so
                # don't blindly assign it to the result
                # panel.result = event.result.data
                self.update_display()

    def on_tool_retry(self, event: ToolRetryEvent):
        """Handle tool retry events."""
        tool_id = event.message.tool_call_id

        # Update the tool call panel with error
        if tool_id in self.panels:
            panel = self.panels[tool_id]
            if isinstance(panel, ToolCallPanel):
                panel.is_complete = True
                panel.is_error = True
                panel.result = event.message.content

        self.update_display()
