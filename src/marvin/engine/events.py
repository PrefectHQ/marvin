import datetime
import uuid
from dataclasses import field
from typing import Generator, Literal

from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from marvin.agents.agent import Agent
from marvin.engine.llm import Message
from marvin.utilities.types import AutoDataClass

EventType = Literal[
    "user-message",
    "tool-return",
    "tool-retry",
    "tool-call",
    "agent-message",
    "orchestrator-start",
    "orchestrator-end",
    "orchestrator-exception",
]


class Event(AutoDataClass):
    _dataclass_config = dict(kw_only=True)

    type: EventType
    id: uuid.UUID = field(default_factory=lambda: uuid.uuid4())
    timestamp: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class UserMessageEvent(Event):
    type: EventType = "user-message"
    message: UserPromptPart


class ToolReturnEvent(Event):
    type: EventType = "tool-return"
    message: ToolReturnPart


class ToolRetryEvent(Event):
    type: EventType = "tool-retry"
    message: RetryPromptPart


class ToolCallEvent(Event):
    type: EventType = "tool-call"
    agent: Agent
    message: ToolCallPart


class AgentMessageEvent(Event):
    type: EventType = "agent-message"
    agent: Agent
    message: TextPart


class OrchestratorStartEvent(Event):
    type: EventType = "orchestrator-start"


class OrchestratorEndEvent(Event):
    type: EventType = "orchestrator-end"


class OrchestratorExceptionEvent(Event):
    type: EventType = "orchestrator-exception"
    error: str


def message_to_events(agent: Agent, message: Message) -> Generator[Event, None, None]:
    for part in message.parts:
        if isinstance(part, UserPromptPart):
            yield UserMessageEvent(message=part)
        elif isinstance(part, ToolReturnPart):
            yield ToolReturnEvent(message=part)
        elif isinstance(part, RetryPromptPart):
            yield ToolRetryEvent(message=part)
        elif isinstance(part, ToolCallPart):
            yield ToolCallEvent(agent=agent, message=part)
        elif isinstance(part, TextPart):
            yield AgentMessageEvent(agent=agent, message=part)
