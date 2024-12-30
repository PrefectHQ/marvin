"""
Event models for Marvin.

Events are stored in a single table but have heterogeneous attributes based on their type.
"""

from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4
from datetime import datetime
from sqlmodel import Field as SQLField, SQLModel, JSON


class EventType(str, Enum):
    """Types of events that can be tracked."""
    USER_MESSAGE = "user_message"
    SYSTEM_MESSAGE = "system_message"
    AGENT_MESSAGE = "agent_message"
    AGENT_MESSAGE_DELTA = "agent_message_delta"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


class Event(SQLModel, table=True):
    """Base event model.
    
    All events are stored in a single table but have different attributes based on their type.
    The attributes are stored in a JSON field and accessed via property methods.
    """
    __tablename__ = "events"
    
    id: str = SQLField(default_factory=lambda: uuid4().hex, primary_key=True)
    event_type: EventType
    timestamp: datetime = SQLField(
        default_factory=lambda: datetime.now(datetime.timezone.utc)
    )
    thread_id: Optional[str] = SQLField(default=None, foreign_key="threads.id")
    parent_id: Optional[str] = SQLField(default=None, foreign_key="events.id")
    agent_id: Optional[str] = SQLField(default=None, foreign_key="agents.id")
    data: Dict[str, Any] = SQLField(default_factory=dict, sa_column=SQLField(JSON))


class UserMessage(Event):
    """A message from the user."""
    event_type: EventType = EventType.USER_MESSAGE
    
    @property
    def message(self) -> str:
        return self.data["message"]
    
    @message.setter
    def message(self, value: str) -> None:
        self.data["message"] = value


class SystemMessage(Event):
    """A system message."""
    event_type: EventType = EventType.SYSTEM_MESSAGE
    
    @property
    def message(self) -> str:
        return self.data["message"]
    
    @message.setter
    def message(self, value: str) -> None:
        self.data["message"] = value


class AgentMessage(Event):
    """A message from an agent."""
    event_type: EventType = EventType.AGENT_MESSAGE
    
    @property
    def message(self) -> str:
        return self.data["message"]
    
    @message.setter
    def message(self, value: str) -> None:
        self.data["message"] = value


class AgentMessageDelta(Event):
    """A partial update to an agent message."""
    event_type: EventType = EventType.AGENT_MESSAGE_DELTA
    
    @property
    def delta(self) -> str:
        return self.data["delta"]
    
    @delta.setter
    def delta(self, value: str) -> None:
        self.data["delta"] = value
    
    @property
    def snapshot(self) -> str:
        return self.data["snapshot"]
    
    @snapshot.setter
    def snapshot(self, value: str) -> None:
        self.data["snapshot"] = value


class ToolCall(Event):
    """A tool call."""
    event_type: EventType = EventType.TOOL_CALL
    
    @property
    def tool_name(self) -> str:
        return self.data["tool_name"]
    
    @tool_name.setter
    def tool_name(self, value: str) -> None:
        self.data["tool_name"] = value
    
    @property
    def inputs(self) -> Dict[str, Any]:
        return self.data["inputs"]
    
    @inputs.setter
    def inputs(self, value: Dict[str, Any]) -> None:
        self.data["inputs"] = value


class ToolResult(Event):
    """The result of a tool call."""
    event_type: EventType = EventType.TOOL_RESULT
    
    @property
    def tool_name(self) -> str:
        return self.data["tool_name"]
    
    @tool_name.setter
    def tool_name(self, value: str) -> None:
        self.data["tool_name"] = value
    
    @property
    def inputs(self) -> Dict[str, Any]:
        return self.data["inputs"]
    
    @inputs.setter
    def inputs(self, value: Dict[str, Any]) -> None:
        self.data["inputs"] = value
    
    @property
    def outputs(self) -> Dict[str, Any]:
        return self.data["outputs"]
    
    @outputs.setter
    def outputs(self, value: Dict[str, Any]) -> None:
        self.data["outputs"] = value
    
    @property
    def error(self) -> Optional[str]:
        return self.data.get("error")
    
    @error.setter
    def error(self, value: Optional[str]) -> None:
        if value is None:
            self.data.pop("error", None)
        else:
            self.data["error"] = value
