"""
Thread management for Marvin.

Threads represent conversations or sequences of events. They can be nested
and associated with tasks.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from .models.models import (
    Thread as DBThread,
    Event,
    Session,
    engine,
)
from .models.events import (
    UserMessage,
    SystemMessage,
    AgentMessage,
    ToolCall,
    ToolResult,
    create_event,
)


class Thread(BaseModel):
    """A conversation thread.
    
    Threads can contain messages, tool calls, and other events.
    """
    
    id: str = Field(default=None)
    name: Optional[str] = None
    parent_id: Optional[str] = None
    
    # Runtime state
    _db_thread: Optional[DBThread] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self._load_or_create_db_thread()
    
    def _load_or_create_db_thread(self) -> None:
        """Load or create the database thread."""
        if not self.id:
            # Create new thread
            with Session(engine) as session:
                db_thread = DBThread(
                    name=self.name,
                    parent_id=self.parent_id,
                )
                session.add(db_thread)
                session.commit()
                session.refresh(db_thread)
                self.id = db_thread.id
                self._db_thread = db_thread
        else:
            # Load existing thread
            with Session(engine) as session:
                self._db_thread = session.get(DBThread, self.id)
                if not self._db_thread:
                    raise ValueError(f"Thread {self.id} not found")
                
                # Update our fields from DB
                self.name = self._db_thread.name
                self.parent_id = self._db_thread.parent_id
                
    @property
    def parent(self) -> Optional["Thread"]:
        """Get the parent thread."""
        if not self.parent_id:
            return None
        return Thread(id=self.parent_id)
    
    
    
    def add_message(
        self,
        content: str,
        role: str = "user",
        name: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> str:
        """Add a message to the thread."""
        if role == "user":
            event = UserMessage(
                content=content,
                name=name,
                thread_id=self.id,
            )
        elif role == "system":
            event = SystemMessage(
                content=content,
                name=name,
                thread_id=self.id,
            )
        elif role == "assistant":
            event = AgentMessage(
                content=content,
                name=name,
                thread_id=self.id,
                agent_id=agent_id,
            )
        else:
            raise ValueError(f"Invalid role: {role}")
        
        return create_event(event)
    
    def add_tool_call(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> str:
        """Add a tool call to the thread."""
        event = ToolCall(
            tool_name=tool_name,
            inputs=inputs,
            thread_id=self.id,
            agent_id=agent_id,
        )
        return create_event(event)
    
    def add_tool_result(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        error: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> str:
        """Add a tool result to the thread."""
        event = ToolResult(
            tool_name=tool_name,
            inputs=inputs,
            outputs=outputs,
            error=error,
            thread_id=self.id,
            parent_id=parent_id,
        )
        return create_event(event)
    
    def get_events(
        self,
        include_children: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Event]:
        """Get events in this thread."""
        from .models import get_events
        return get_events(
            thread_id=self.id,
            include_children=include_children,
            limit=limit,
            offset=offset,
        )
    
    
    @classmethod
    def get(cls, thread_id: str) -> "Thread":
        """Get a thread by ID."""
        return cls(id=thread_id)
    
    @classmethod
    def create(
        cls,
        name: Optional[str] = None,
        parent_id: Optional[str] = None,
        
    ) -> "Thread":
        """Create a new thread."""
        return cls(
            name=name,
            parent_id=parent_id,
        )
