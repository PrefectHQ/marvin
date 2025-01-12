"""Agents for Marvin.

An Agent is an entity that can process tasks and maintain state across interactions.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

import pydantic_ai
from pydantic_ai.models import KnownModelName, Model, ModelSettings

import marvin
import marvin.engine.llm
from marvin.agents.names import AGENT_NAMES
from marvin.agents.team import SoloTeam, Swarm, Team
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.tools.thread import post_message

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

    model: KnownModelName | Model | None = field(
        default=None,
        metadata={
            "description": "The model to use for the agent. If not provided, the default model will be used. A compatible string can be passed to automatically retrieve the model.",
        },
        repr=False,
    )

    model_settings: ModelSettings = field(
        default_factory=ModelSettings,
        metadata={"description": "Settings to pass to the model"},
        repr=False,
    )

    delegates: list[Actor] | None = field(
        default=None,
        repr=False,
        metadata={
            "description": "List of agents that this agent can delegate to. Provide an empty list if this agent can not delegate.",
        },
    )

    prompt: str | Path = field(
        default=Path("agent.jinja"),
        metadata={"description": "Template for the agent's prompt"},
        repr=False,
    )

    def __hash__(self) -> int:
        return super().__hash__()

    def friendly_name(self) -> str:
        return f'Agent "{self.name}" ({self.id})'

    def get_delegates(self) -> list[Actor] | None:
        return self.delegates

    def get_model(self) -> Model | KnownModelName:
        return self.model or marvin.defaults.model

    def get_tools(self) -> list[Callable[..., Any]]:
        return (
            self.tools
            + [t for m in self.memories for t in m.get_tools()]
            + [post_message]
        )

    def get_model_settings(self) -> ModelSettings:
        defaults: ModelSettings = {}
        if marvin.settings.agent_temperature is not None:
            defaults["temperature"] = marvin.settings.agent_temperature
        return defaults | self.model_settings

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

    def as_team(self, team_class: Callable[[list[Actor]], Team] | None = None) -> Team:
        all_agents = [self] + (self.delegates or [])
        if len(all_agents) == 1:
            team_class = team_class or SoloTeam
        else:
            team_class = team_class or Swarm
        return team_class(agents=all_agents)
