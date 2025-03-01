import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import partial_json_parser
from pydantic_ai.messages import (
    FinalResultEvent,
    ModelResponsePart,
    RetryPromptPart,
    TextPart,
    TextPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.result import FinalResult

from marvin.agents.actor import Actor
from marvin.engine.end_turn import EndTurn

# Define event types as literals for type checking
EventType = Literal[
    "user-message",
    "tool-result",
    "tool-retry",
    "tool-call",
    "tool-call-delta",
    "actor-message",
    "actor-message-delta",
    "orchestrator-start",
    "orchestrator-end",
    "orchestrator-error",
    "actor-start-turn",
    "actor-end-turn",
    "end-turn-tool-call",
    "end-turn-tool-result",
]


@dataclass(kw_only=True)
class Event:
    """Base class for all events in the system."""

    _dataclass_config = dict(kw_only=True)

    type: EventType
    id: uuid.UUID = field(default_factory=lambda: uuid.uuid4())
    timestamp: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


@dataclass(kw_only=True)
class UserMessageEvent(Event):
    """Event for user messages."""

    type: EventType = field(default="user-message", init=False)
    message: UserPromptPart


@dataclass(kw_only=True)
class ToolResultEvent(Event):
    """Event for tool return values."""

    type: EventType = field(default="tool-result", init=False)
    message: ToolReturnPart


@dataclass(kw_only=True)
class ToolRetryEvent(Event):
    """Event for tool retry requests."""

    type: EventType = field(default="tool-retry", init=False)
    message: RetryPromptPart


@dataclass(kw_only=True)
class ToolCallEvent(Event):
    """Event for complete tool calls ready to be executed."""

    type: EventType = field(default="tool-call", init=False)
    actor: Actor
    message: ToolCallPart
    tool_call_id: str
    tool: Callable[..., Any] | None

    def args_dict(self) -> dict[str, Any]:
        """Return the args as a dictionary."""
        if self.message.args and isinstance(self.message.args, str):
            return partial_json_parser.loads(self.message.args)
        return self.message.args


@dataclass(kw_only=True)
class EndTurnToolCallEvent(Event):
    """Event that fires as soon as we know that an end turn tool call has been made."""

    type: EventType = field(default="end-turn-tool-call", init=False)
    actor: Actor
    event: FinalResultEvent
    tool_call_id: str
    tool: EndTurn


@dataclass(kw_only=True)
class EndTurnToolResultEvent(Event):
    """Event for the final result from an end turn tool."""

    type: EventType = field(default="end-turn-tool-result", init=False)
    actor: Actor
    result: FinalResult
    tool_call_id: str
    tool: EndTurn


@dataclass(kw_only=True)
class ToolCallDeltaEvent(Event):
    """Event for delta updates to tool calls during streaming."""

    type: EventType = field(default="tool-call-delta", init=False)
    actor: Actor
    delta: ToolCallPartDelta
    snapshot: ToolCallPart
    tool_call_id: str
    tool: Callable[..., Any] | None

    def args_dict(self) -> dict[str, Any]:
        """Return the args as a dictionary."""
        if self.snapshot.args and isinstance(self.snapshot.args, str):
            return partial_json_parser.loads(self.snapshot.args)
        return self.snapshot.args


@dataclass(kw_only=True)
class ActorMessageEvent(Event):
    """Event for complete text messages from an agent."""

    type: EventType = field(default="actor-message", init=False)
    actor: Actor
    message: TextPart


@dataclass(kw_only=True)
class ActorMessageDeltaEvent(Event):
    """Event for delta updates to agent messages during streaming."""

    type: EventType = field(default="actor-message-delta", init=False)
    actor: Actor
    delta: TextPartDelta
    snapshot: TextPart


@dataclass(kw_only=True)
class OrchestratorStartEvent(Event):
    """Event for orchestrator start."""

    type: EventType = field(default="orchestrator-start", init=False)


@dataclass(kw_only=True)
class OrchestratorEndEvent(Event):
    """Event for orchestrator end."""

    type: EventType = field(default="orchestrator-end", init=False)


@dataclass(kw_only=True)
class OrchestratorErrorEvent(Event):
    """Event for orchestrator exceptions."""

    type: EventType = field(default="orchestrator-error", init=False)
    error: str


@dataclass(kw_only=True)
class ActorStartTurnEvent(Event):
    """Event for agent turn start."""

    type: EventType = field(default="actor-start-turn", init=False)
    actor: Actor


@dataclass(kw_only=True)
class ActorEndTurnEvent(Event):
    """Event for agent turn end."""

    type: EventType = field(default="actor-end-turn", init=False)
    actor: Actor


# Helper function to extract text from parts
def get_text_from_parts(parts: list[ModelResponsePart]) -> str:
    """Extract text content from a list of ModelResponseParts."""
    text_parts = []
    for part in parts:
        if isinstance(part, TextPart):
            text_parts.append(part.content)
    return "".join(text_parts)
