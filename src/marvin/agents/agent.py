"""
Agents for Marvin.

An Agent is an entity that can process tasks and maintain state across interactions.
"""

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Union

import pydantic_ai
from pydantic_ai.models import KnownModelName, Model, ModelSettings

import marvin
import marvin.engine.llm
from marvin.agents.names import AGENT_NAMES
from marvin.engine.thread import Thread, get_thread
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.utilities.asyncio import run_sync

from .actor import Actor


@dataclass(kw_only=True)
class Agent(Actor):
    """An agent that can process tasks and maintain state."""

    name: str = field(
        default_factory=lambda: random.choice(AGENT_NAMES),
        metadata={"description": "Name of the agent"},
        kw_only=False,
    )

    tools: list[Callable[..., Any]] = field(
        default_factory=list,
        metadata={"description": "List of tools available to the agent"},
    )

    memories: list[Memory] = field(
        default_factory=list,
        metadata={"description": "List of memory modules available to the agent"},
    )

    model: Optional[KnownModelName | Model] = field(
        default=None,
        metadata={
            "description": "The model to use for the agent. If not provided, the default model will be used. A compatible string can be passed to automatically retrieve the model."
        },
    )

    model_settings: ModelSettings = field(
        default_factory=ModelSettings,
        metadata={"description": "Settings to pass to the model"},
    )

    delegates: list[Actor] | None = field(
        default=None,
        repr=False,
        metadata={
            "description": "List of agents that this agent can delegate to. Provide an empty list if this agent can not delegate."
        },
    )

    prompt: str | Path = field(
        default=Path("agent.jinja"),
        metadata={"description": "Template for the agent's prompt"},
    )

    def get_delegates(self) -> list[Actor] | None:
        return self.delegates

    def get_model(self) -> Model | KnownModelName:
        return self.model or marvin.defaults.model

    def get_tools(self) -> list[Callable[..., Any]]:
        return self.tools + [t for m in self.memories for t in m.get_tools()]

    def get_model_settings(self) -> ModelSettings:
        defaults: ModelSettings = {}
        if marvin.settings.agent_temperature is not None:
            defaults["temperature"] = marvin.settings.agent_temperature
        return defaults | self.model_settings

    async def say_async(self, message: str, thread: Thread | str | None = None):
        thread = get_thread(thread)
        if message:
            await thread.add_user_message_async(message=message)
        return await marvin.run_async("Respond to the user.", agent=self, thread=thread)

    def say(self, message: str, thread: Thread | str | None = None):
        return run_sync(self.say_async(message, thread))

    def get_agentlet(
        self,
        result_types: list[type],
        tools: list[Callable[..., Any]] | None = None,
        **kwargs,
    ) -> pydantic_ai.Agent[Any, Any]:
        return pydantic_ai.Agent[None, result_types](
            model=self.get_model(),
            result_type=Union[tuple(result_types)],  # type: ignore
            tools=self.get_tools() + (tools or []),
            model_settings=self.get_model_settings(),
            end_strategy="exhaustive",
            **kwargs,
        )

    def get_prompt(self) -> str:
        return Template(source=self.prompt).render(agent=self)
