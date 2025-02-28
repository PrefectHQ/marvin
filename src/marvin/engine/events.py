import datetime
import uuid
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Literal

from pydantic_ai._parts_manager import ModelResponsePartsManager
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelResponsePart,
    ModelResponseStreamEvent,
    PartDeltaEvent,
    PartStartEvent,
    RetryPromptPart,
    TextPart,
    TextPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
    ToolReturnPart,
    UserPromptPart,
)

from marvin.agents.actor import Actor
from marvin.engine.llm import Message

EventType = Literal[
    "user-message",
    "tool-return",
    "tool-retry",
    "tool-call",
    "actor-message",
    "orchestrator-start",
    "orchestrator-end",
    "orchestrator-exception",
    "actor-start-turn",
    "actor-end-turn",
    "stream-start",
    "stream-end",
    "stream-text-delta",
    "stream-tool-call-start",
    "stream-tool-call-delta",
    "stream-tool-call-complete",
    "stream-tool-result",
]


@dataclass(kw_only=True)
class Event:
    _dataclass_config = dict(kw_only=True)

    type: EventType
    id: uuid.UUID = field(default_factory=lambda: uuid.uuid4())
    timestamp: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


@dataclass(kw_only=True)
class UserMessageEvent(Event):
    type: EventType = field(default="user-message", init=False)
    message: UserPromptPart


@dataclass(kw_only=True)
class ToolReturnEvent(Event):
    type: EventType = field(default="tool-return", init=False)
    message: ToolReturnPart


@dataclass(kw_only=True)
class ToolRetryEvent(Event):
    type: EventType = field(default="tool-retry", init=False)
    message: RetryPromptPart


@dataclass(kw_only=True)
class ToolCallEvent(Event):
    type: EventType = field(default="tool-call", init=False)
    actor: Actor
    message: ToolCallPart


@dataclass(kw_only=True)
class AgentMessageEvent(Event):
    type: EventType = field(default="actor-message", init=False)
    actor: Actor
    message: TextPart


@dataclass(kw_only=True)
class OrchestratorStartEvent(Event):
    type: EventType = field(default="orchestrator-start", init=False)


@dataclass(kw_only=True)
class OrchestratorEndEvent(Event):
    type: EventType = field(default="orchestrator-end", init=False)


@dataclass(kw_only=True)
class OrchestratorExceptionEvent(Event):
    type: EventType = field(default="orchestrator-exception", init=False)
    error: str


def message_to_events(actor: Actor, message: Message) -> Generator[Event, None, None]:  # noqa: F821
    for part in message.parts:
        if isinstance(part, UserPromptPart) and part.content:
            yield UserMessageEvent(message=part)
        elif isinstance(part, ToolReturnPart):
            yield ToolReturnEvent(message=part)
        elif isinstance(part, RetryPromptPart):
            yield ToolRetryEvent(message=part)
        elif isinstance(part, ToolCallPart):
            yield ToolCallEvent(actor=actor, message=part)
        elif isinstance(part, TextPart):
            yield AgentMessageEvent(actor=actor, message=part)


@dataclass(kw_only=True)
class AgentStartTurnEvent(Event):
    type: EventType = field(default="actor-start-turn", init=False)
    actor: Actor


@dataclass(kw_only=True)
class AgentEndTurnEvent(Event):
    type: EventType = field(default="actor-end-turn", init=False)
    actor: Actor


# ----- Streaming Events -----


@dataclass(kw_only=True)
class StreamingEvent(Event):
    """Base class for all streaming events."""

    actor: Actor


@dataclass(kw_only=True)
class StreamStartEvent(StreamingEvent):
    """Event emitted when a streaming response starts."""

    type: EventType = field(default="stream-start", init=False)


@dataclass(kw_only=True)
class StreamEndEvent(StreamingEvent):
    """Event emitted when a streaming response ends."""

    type: EventType = field(default="stream-end", init=False)


@dataclass(kw_only=True)
class StreamTextDeltaEvent(StreamingEvent):
    """Event emitted when a text delta is received during streaming."""

    type: EventType = field(default="stream-text-delta", init=False)
    content_delta: str
    content_snapshot: str


@dataclass(kw_only=True)
class StreamToolCallStartEvent(StreamingEvent):
    """Event emitted when a tool call starts during streaming."""

    type: EventType = field(default="stream-tool-call-start", init=False)
    tool_name: str
    tool_call_id: str | None = None


@dataclass(kw_only=True)
class StreamToolCallDeltaEvent(StreamingEvent):
    """Event emitted when a tool call parameter is streamed."""

    type: EventType = field(default="stream-tool-call-delta", init=False)
    tool_name_delta: str | None
    args_delta: str | dict | None
    args_snapshot: str | dict | None
    tool_call_id: str | None = None


@dataclass(kw_only=True)
class StreamToolCallCompleteEvent(StreamingEvent):
    """Event emitted when a tool call is complete."""

    type: EventType = field(default="stream-tool-call-complete", init=False)
    tool_name: str
    args: str | dict
    tool_call_id: str | None = None


@dataclass(kw_only=True)
class StreamToolResultEvent(StreamingEvent):
    """Event emitted when a tool call returns a result."""

    type: EventType = field(default="stream-tool-result", init=False)
    tool_name: str
    result: str
    tool_call_id: str | None = None


# Helper function to convert a list of ModelResponseParts to a readable form
def get_text_from_parts(parts: list[ModelResponsePart]) -> str:
    """Extract text content from a list of ModelResponseParts.

    This assumes the parts are ordered correctly.
    """
    text_parts = []
    for part in parts:
        if isinstance(part, TextPart):
            text_parts.append(part.content)
    return "".join(text_parts)


async def handle_pydantic_event(
    event: ModelResponseStreamEvent,
    actor: Actor,
    parts_manager: ModelResponsePartsManager,
) -> Generator[Event, None, None]:
    """Convert a pydantic-ai streaming event to Marvin events.

    This function:
    1. Processes a pydantic-ai event
    2. Updates the parts manager's state
    3. Yields appropriate Marvin events

    Args:
        event: A pydantic-ai event from the streaming API
        actor: The actor that generated this event
        parts_manager: A ModelResponsePartsManager to track accumulated state

    Yields:
        Marvin events created from this pydantic event
    """
    # Process the event with the parts manager to accumulate the delta
    if isinstance(event, PartStartEvent):
        # A new part has started
        if event.part.part_kind == "text":
            # For text parts, use handle_text_delta
            parts_manager.handle_text_delta(
                vendor_part_id=event.index, content=event.part.content
            )
            # Get current snapshot for text so far
            current_parts = parts_manager.get_parts()
            content_snapshot = get_text_from_parts(current_parts)

            # Create a start event
            start_event = StreamStartEvent(actor=actor)
            yield start_event

            # Create a text delta event
            text_event = StreamTextDeltaEvent(
                actor=actor,
                content_delta=event.part.content,
                content_snapshot=content_snapshot,
            )
            yield text_event

        elif event.part.part_kind == "tool-call":
            # For tool call parts, use handle_tool_call_part
            parts_manager.handle_tool_call_part(
                vendor_part_id=event.index,
                tool_name=event.part.tool_name,
                args=event.part.args,
                tool_call_id=event.part.tool_call_id,
            )

            # Create a tool call start event
            tool_start_event = StreamToolCallStartEvent(
                actor=actor,
                tool_name=event.part.tool_name,
                tool_call_id=event.part.tool_call_id,
            )
            yield tool_start_event

            # If we have complete args, also create a tool call complete event
            tool_complete_event = StreamToolCallCompleteEvent(
                actor=actor,
                tool_name=event.part.tool_name,
                args=event.part.args,
                tool_call_id=event.part.tool_call_id,
            )
            yield tool_complete_event

    elif isinstance(event, PartDeltaEvent):
        # An existing part has been updated
        if isinstance(event.delta, TextPartDelta):
            # Handle text delta
            parts_manager.handle_text_delta(
                vendor_part_id=event.index, content=event.delta.content_delta
            )

            # Get current snapshot for text so far
            current_parts = parts_manager.get_parts()
            content_snapshot = get_text_from_parts(current_parts)

            # Create a text delta event
            text_event = StreamTextDeltaEvent(
                actor=actor,
                content_delta=event.delta.content_delta,
                content_snapshot=content_snapshot,
            )
            yield text_event

        elif isinstance(event.delta, ToolCallPartDelta):
            # Handle tool call delta
            parts_manager.handle_tool_call_delta(
                vendor_part_id=event.index,
                tool_name=event.delta.tool_name_delta,
                args=event.delta.args_delta,
                tool_call_id=event.delta.tool_call_id,
            )

            # Get current state of the tool call
            current_parts = parts_manager.get_parts()
            tool_call_part = None
            for part in current_parts:
                if (
                    isinstance(part, ToolCallPart)
                    and isinstance(event.index, int)
                    and part == current_parts[event.index]
                ):
                    tool_call_part = part
                    break

            # Create a tool call delta event
            if tool_call_part:
                tool_delta_event = StreamToolCallDeltaEvent(
                    actor=actor,
                    tool_name_delta=event.delta.tool_name_delta,
                    args_delta=event.delta.args_delta,
                    args_snapshot=tool_call_part.args,
                    tool_call_id=event.delta.tool_call_id,
                )
                yield tool_delta_event

    elif isinstance(event, FunctionToolCallEvent):
        # Tool call event - A tool is about to be called
        # Create a tool call complete event (the args are complete)
        tool_complete_event = StreamToolCallCompleteEvent(
            actor=actor,
            tool_name=event.part.tool_name,
            args=event.part.args,
            tool_call_id=event.part.tool_call_id,
        )
        yield tool_complete_event

    elif isinstance(event, FunctionToolResultEvent):
        # Tool result event - A tool has returned a result
        # Create a tool result event
        tool_result_event = StreamToolResultEvent(
            actor=actor,
            tool_name=event.tool_name or "unknown_tool",
            result=event.result.content,
            tool_call_id=event.tool_call_id,
        )
        yield tool_result_event

    elif isinstance(event, FinalResultEvent):
        # Final result event - The model has completed its response
        # Create a stream end event
        end_event = StreamEndEvent(actor=actor)
        yield end_event
