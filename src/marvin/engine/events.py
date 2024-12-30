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


class Event(AutoDataClass):
    _dataclass_config = dict(kw_only=True)

    type: str
    id: uuid.UUID = field(default_factory=lambda: uuid.uuid4())
    timestamp: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class UserMessageEvent(Event):
    type: Literal["user-message"] = "user-message"
    message: UserPromptPart


class ToolReturnEvent(Event):
    type: Literal["tool-return"] = "tool-return"
    message: ToolReturnPart


class ToolRetryEvent(Event):
    type: Literal["tool-retry"] = "tool-retry"
    message: RetryPromptPart


class ToolCallEvent(Event):
    type: Literal["tool-call"] = "tool-call"
    agent: Agent
    message: ToolCallPart


class AgentMessageEvent(Event):
    type: Literal["agent-message"] = "agent-message"
    agent: Agent
    message: TextPart


class OrchestratorStartEvent(Event):
    type: Literal["orchestrator-start"] = "orchestrator-start"


class OrchestratorEndEvent(Event):
    type: Literal["orchestrator-end"] = "orchestrator-end"


class OrchestratorExceptionEvent(Event):
    type: Literal["orchestrator-exception"] = "orchestrator-exception"
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
