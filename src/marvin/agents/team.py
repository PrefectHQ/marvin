import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Self

import pydantic_ai

from marvin.agents.actor import Actor
from marvin.agents.names import TEAM_NAMES
from marvin.engine.end_turn_tools import DelegateToAgent
from marvin.prompts import Template

if TYPE_CHECKING:
    from marvin.engine.end_turn_tools import EndTurn


@dataclass(kw_only=True)
class Team(Actor):
    agents: list[Actor]
    tools: list[Callable[..., Any]] = field(default_factory=list)
    name: str = field(
        default_factory=lambda: random.choice(TEAM_NAMES),
        metadata={"description": "Name of the team"},
    )

    prompt: str | Path = field(
        default=Path("team.jinja"),
        metadata={"description": "Template for the team's prompt"},
    )

    _active_agent: Actor = field(init=False)

    def get_delegates(self) -> list[Actor]:
        """
        By default, agents can delegate only to pre-defined agents. If no delegates are defined,
        none are returned.
        """
        delegates = self.active_agent.get_delegates()
        return delegates or []

    def __post_init__(self):
        self.agents_by_id = {a.id: a for a in self.agents}
        self.active_agent = self.agents[0]

    def get_agentlet(
        self,
        result_types: list[type],
        tools: list[Callable[..., Any]] | None = None,
        **kwargs,
    ) -> pydantic_ai.Agent[Any, Any]:
        return self._active_agent.get_agentlet(
            tools=self.tools + self.get_end_turn_tools() + (tools or []),
            result_types=result_types,
            **kwargs,
        )

    @property
    def active_agent(self) -> Actor:
        return self._active_agent

    @active_agent.setter
    def active_agent(self, agent: Actor):
        self._active_agent = agent

    def get_prompt(self) -> str:
        return Template(source=self.prompt).render(team=self)

    def get_end_turn_tools(self) -> list[type["EndTurn"]]:
        return []

    def as_team(self) -> Self:
        return self

    def start_turn(self):
        if self.active_agent:
            self.active_agent.start_turn()

    def end_turn(self):
        if self.active_agent:
            self.active_agent.end_turn()


@dataclass(kw_only=True)
class SoloTeam(Team):
    prompt: str | Path = Path("agent.jinja")

    def __post_init__(self):
        if len(self.agents) != 1:
            raise ValueError("SoloTeam must have exactly one agent")
        super().__post_init__()

    def get_delegates(self) -> list[Actor]:
        return []

    def get_prompt(self) -> str:
        return self.agents[0].get_prompt()


@dataclass(kw_only=True)
class Swarm(Team):
    """
    A swarm is a team that permits all agents to delegate to each other.
    """

    instructions: str | None = (
        "Delegate to other agents as necessary in order to achieve the goal quickly."
    )

    def get_delegates(self) -> list[Actor]:
        delegates = self.active_agent.get_delegates()
        if delegates is None:
            return self.agents
        else:
            return delegates

    def get_end_turn_tools(self) -> list[type["EndTurn"]]:
        return [DelegateToAgent]


@dataclass(kw_only=True)
class RoundRobinTeam(Team):
    def start_turn(self):
        index = self.agents.index(self.active_agent)
        self.active_agent = self.agents[(index + 1) % len(self.agents)]
        super().start_turn()


@dataclass(kw_only=True)
class RandomTeam(Team):
    def start_turn(self):
        self.set_active_agent(random.choice(self.agents))
        super().start_turn()
