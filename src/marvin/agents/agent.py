"""
Agents for Marvin.

An Agent is an entity that can process tasks and maintain state across interactions.
"""

import uuid
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
import random
from marvin.agents.names import AGENT_NAMES
from marvin.engine.thread import Thread, get_thread
from marvin.tools.tools import Tool
import marvin
import marvin.engine.llm

from marvin.utilities.asyncio import run_sync
from .actor import Actor


@dataclass
class Agent(Actor):
    """An agent that can process tasks and maintain state."""

    id: uuid.UUID = field(
        default_factory=uuid.uuid4,
        metadata={"description": "Unique identifier for this agent"},
    )

    instructions: Optional[str] = field(
        default=None, metadata={"description": "Instructions for the agent"}
    )

    tools: list[Tool | Callable] = field(
        default_factory=list,
        metadata={"description": "List of tools available to the agent"},
    )

    name: Optional[str] = field(
        default_factory=lambda: random.choice(AGENT_NAMES),
        metadata={"description": "Name of the agent"},
    )

    model: Optional[str] = field(
        default=None,
        metadata={
            "description": "The model to use for the agent. If not provided, the default model will be used. A compatible string can be passed to automatically retrieve the model."
        },
    )

    model_kwargs: dict[str, Any] = field(
        default_factory=dict,
        metadata={"description": "Keyword arguments to pass to the model"},
    )

    def get_model(self):
        return self.model or marvin.defaults.model

    async def say_async(self, message: str, thread: Thread | str = None):
        thread = get_thread(thread)
        await thread.add_user_message(message=message)
        return await marvin.run_async("Respond to the user.", agent=self, thread=thread)

    def say(self, message: str, thread: Thread | str = None):
        return run_sync(self.say_async(message, thread))
