import random
from dataclasses import field
from typing import Callable

import pydantic_ai

from marvin.agents.actor import Actor
from marvin.agents.names import TEAM_NAMES


class Team(Actor):
    _dataclass_config = {"kw_only": True}

    agents: list[Actor]
    tools: list[Callable] = field(default_factory=list)
    name: str = field(
        default_factory=lambda: random.choice(TEAM_NAMES),
        metadata={"description": "Name of the team"},
    )

    _active_agent: Actor = field(init=False)

    def __post_init__(self):
        self.set_active_agent(self.agents[0])

    def get_agentlet(
        self,
        result_types: list[type],
        tools: list[Callable] = None,
    ) -> pydantic_ai.Agent:
        return self._active_agent.get_agentlet(
            tools=self.tools + (tools or []), result_types=result_types
        )

    def get_active_agent(self) -> Actor:
        return self._active_agent

    def set_active_agent(self, agent: Actor):
        self._active_agent = agent
