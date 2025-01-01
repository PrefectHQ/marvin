"""
Agents for Marvin.

An Agent is an entity that can process tasks and maintain state across interactions.
"""

import random
import uuid
from dataclasses import field
from typing import Callable, Optional, Union

import pydantic_ai
from pydantic_ai.models import Model, ModelSettings

import marvin
import marvin.engine.llm
from marvin.agents.names import AGENT_NAMES
from marvin.engine.thread import Thread, get_thread
from marvin.memory.memory import Memory
from marvin.utilities.asyncio import run_sync

from .actor import Actor


class Agent(Actor):
    """An agent that can process tasks and maintain state."""

    _dataclass_config = {"kw_only": True}

    id: uuid.UUID = field(
        default_factory=uuid.uuid4,
        metadata={"description": "Unique identifier for this agent"},
    )

    instructions: Optional[str] = field(
        default=None, metadata={"description": "Instructions for the agent"}
    )

    tools: list[Callable] = field(
        default_factory=list,
        metadata={"description": "List of tools available to the agent"},
    )

    memories: list[Memory] = field(
        default_factory=list,
        metadata={"description": "List of memory modules available to the agent"},
    )

    name: str = field(
        default_factory=lambda: random.choice(AGENT_NAMES),
        metadata={"description": "Name of the agent"},
    )

    model: Optional[str | Model] = field(
        default=None,
        metadata={
            "description": "The model to use for the agent. If not provided, the default model will be used. A compatible string can be passed to automatically retrieve the model."
        },
    )

    model_settings: ModelSettings = field(
        default_factory=dict,
        metadata={"description": "Settings to pass to the model"},
    )

    def get_model(self):
        return self.model or marvin.defaults.model

    def get_tools(self) -> list[Callable]:
        return self.tools + [t for m in self.memories for t in m.get_tools()]

    def get_model_settings(self) -> ModelSettings:
        defaults = {}
        if marvin.settings.agent_temperature is not None:
            defaults["temperature"] = marvin.settings.agent_temperature
        return defaults | self.model_settings

    async def say_async(self, message: str, thread: Thread | str = None):
        thread = get_thread(thread)
        await thread.add_user_message(message=message)
        return await marvin.run_async("Respond to the user.", agent=self, thread=thread)

    def say(self, message: str, thread: Thread | str = None):
        return run_sync(self.say_async(message, thread))

    def get_agentlet(
        self,
        result_types: list[type],
        tools: list[Callable] = None,
    ) -> pydantic_ai.Agent:
        return marvin.engine.llm.create_agentlet(
            model=self.get_model(),
            result_type=Union[tuple(result_types)],
            tools=self.get_tools() + (tools or []),
            model_settings=self.get_model_settings(),
        )
