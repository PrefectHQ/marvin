import random
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pydantic_ai
from typing_extensions import Self

from marvin.agents.actor import Actor
from marvin.agents.names import TEAM_NAMES
from marvin.engine.end_turn import DelegateToAgent
from marvin.memory.memory import Memory
from marvin.prompts import Template

if TYPE_CHECKING:
    from marvin.engine.end_turn import EndTurn


@dataclass(kw_only=True)
class Team(Actor):
    agents: list[Actor]
    name: str = field(
        default_factory=lambda: random.choice(TEAM_NAMES),
        metadata={"description": "Name of the team"},
    )

    prompt: str | Path = field(
        default=Path("team.jinja"),
        metadata={"description": "Template for the team's prompt"},
    )

    allow_message_posting: bool = field(
        default=True,
        metadata={
            "description": "Whether to allow the team to post messages to the thread",
        },
    )

    active_agent: Actor = field(init=False)

    def __hash__(self) -> int:
        return super().__hash__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, agents={[a.name for a in self.agents]})"

    def get_delegates(self) -> list[Actor]:
        """By default, agents can delegate only to pre-defined agents. If no delegates are defined,
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
        return self.active_agent.get_agentlet(
            tools=self.get_end_turn_tools() + (tools or []),
            result_types=result_types,
            **kwargs,
        )

    def get_prompt(self) -> str:
        return Template(source=self.prompt).render(team=self)

    def get_tools(self) -> list[Callable[..., Any]]:
        return self.active_agent.get_tools()

    def get_memories(self) -> list[Memory]:
        return self.active_agent.get_memories()

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

    def __repr__(self) -> str:
        return super().__repr__()

    def __hash__(self) -> int:
        return super().__hash__()

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
    """A swarm is a team that permits all agents to delegate to each other."""

    instructions: str | None = None

    description: str | None = "A team of agents that can delegate to each other."

    def __repr__(self) -> str:
        return super().__repr__()

    def __hash__(self) -> int:
        return super().__hash__()

    def get_delegates(self) -> list[Actor]:
        delegates = self.active_agent.get_delegates()
        if delegates is None:
            return [a for a in self.agents if a is not self.active_agent]
        return delegates

    def get_end_turn_tools(self) -> list[type["EndTurn"]]:
        return [DelegateToAgent]


@dataclass(kw_only=True)
class RoundRobinTeam(Team):
    description: str | None = "A team of agents that rotate turns."

    def __repr__(self) -> str:
        return super().__repr__()

    def __hash__(self) -> int:
        return super().__hash__()

    def start_turn(self):
        index = self.agents.index(self.active_agent)
        self.active_agent = self.agents[(index + 1) % len(self.agents)]
        super().start_turn()


@dataclass(kw_only=True)
class RandomTeam(Team):
    description: str | None = "A team of agents that randomly selects an agent to act."

    def __repr__(self) -> str:
        return super().__repr__()

    def __hash__(self) -> int:
        return super().__hash__()

    def start_turn(self):
        self.active_agent = random.choice(self.agents)
        super().start_turn()
