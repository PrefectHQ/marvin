import datetime
import uuid
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Literal

import pydantic_ai
import pydantic_ai._result
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from marvin.agents.agent import Agent
from marvin.engine.end_turn import EndTurn
from marvin.engine.llm import Message
from marvin.utilities.types import issubclass_safe

EventType = Literal[
    "user-message",
    "tool-return",
    "tool-retry",
    "tool-call",
    "agent-message",
    "orchestrator-start",
    "orchestrator-end",
    "orchestrator-exception",
    "agent-start-turn",
    "agent-end-turn",
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
    end_turn_tool: EndTurn | None = None


@dataclass(kw_only=True)
class ToolRetryEvent(Event):
    type: EventType = field(default="tool-retry", init=False)
    message: RetryPromptPart
    end_turn_tool: EndTurn | None = None


@dataclass(kw_only=True)
class ToolCallEvent(Event):
    type: EventType = field(default="tool-call", init=False)
    agent: Agent
    message: ToolCallPart
    end_turn_tool: EndTurn | None = None


@dataclass(kw_only=True)
class AgentMessageEvent(Event):
    type: EventType = field(default="agent-message", init=False)
    agent: Agent
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


def message_to_events(
    agent: Agent,
    message: Message,
    agentlet: pydantic_ai.Agent = None,
    end_turn_tools: list[EndTurn] = [],
) -> Generator[Event, None, None]:  # noqa: F821
    for part in message.parts:
        if isinstance(part, UserPromptPart) and part.content:
            yield UserMessageEvent(message=part)
        elif isinstance(part, ToolReturnPart):
            end_turn_tool = agentlet._result_schema.tools.get(part.tool_name)
            if end_turn_tool:
                end_turn_tool = end_turn_tool.type_adapter._type

            end_turn_tools
            yield ToolReturnEvent(
                message=part,
                end_turn_tool=end_turn_tool,
            )
        elif isinstance(part, RetryPromptPart):
            end_turn_tool = agentlet._result_schema.tools.get(part.tool_name)
            if end_turn_tool:
                end_turn_tool = end_turn_tool.type_adapter._type

            yield ToolRetryEvent(
                message=part,
                end_turn_tool=end_turn_tool,
            )
        elif isinstance(part, ToolCallPart):
            end_turn_tool = agentlet._result_schema.tools.get(part.tool_name)
            if end_turn_tool:
                end_turn_tool = end_turn_tool.type_adapter._type
                if issubclass_safe(end_turn_tool, dict):
                    end_turn_tool = end_turn_tool.__annotations__.get("response")

            yield ToolCallEvent(
                agent=agent,
                message=part,
                end_turn_tool=end_turn_tool,
            )
        elif isinstance(part, TextPart):
            yield AgentMessageEvent(agent=agent, message=part)


@dataclass(kw_only=True)
class AgentStartTurnEvent(Event):
    type: EventType = field(default="agent-start-turn", init=False)
    agent: Agent


@dataclass(kw_only=True)
class AgentEndTurnEvent(Event):
    type: EventType = field(default="agent-end-turn", init=False)
    agent: Agent
