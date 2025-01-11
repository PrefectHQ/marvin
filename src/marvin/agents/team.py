import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Self

import pydantic_ai

from marvin.agents.actor import Actor
from marvin.agents.names import TEAM_NAMES
from marvin.engine.end_turn import DelegateToAgent
from marvin.prompts import Template

if TYPE_CHECKING:
    from marvin.engine.end_turn import EndTurn


@dataclass(kw_only=True)
class Team(Actor):
    members: list[Actor]
    tools: list[Callable[..., Any]] = field(default_factory=list)
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
            "description": "Whether to allow the team to post messages to the thread"
        },
    )

    _active_member: Actor = field(init=False)

    def __hash__(self) -> int:
        return super().__hash__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={repr(self.name)}, agents={[a.name for a in self.members]})"

    def get_delegates(self) -> list[Actor]:
        """
        By default, agents can delegate only to pre-defined agents. If no delegates are defined,
        none are returned.
        """
        delegates = self.active_member.get_delegates()
        return delegates or []

    def __post_init__(self):
        self.agents_by_id = {a.id: a for a in self.members}
        self.active_member = self.members[0]

    def get_agentlet(
        self,
        result_types: list[type],
        tools: list[Callable[..., Any]] | None = None,
        **kwargs,
    ) -> pydantic_ai.Agent[Any, Any]:
        return self.active_member.get_agentlet(
            tools=self.tools + self.get_end_turn_tools() + (tools or []),
            result_types=result_types,
            **kwargs,
        )

    @property
    def active_member(self) -> Actor:
        return self._active_member

    @active_member.setter
    def active_member(self, agent: Actor):
        self._active_member = agent

    def get_prompt(self) -> str:
        return Template(source=self.prompt).render(team=self)

    def get_tools(self) -> list[Callable[..., Any]]:
        tools = self.tools + self.active_member.get_tools()
        return tools

    def get_end_turn_tools(self) -> list[type["EndTurn"]]:
        return []

    def as_team(self) -> Self:
        return self

    def start_turn(self):
        if self.active_member:
            self.active_member.start_turn()

    def end_turn(self):
        if self.active_member:
            self.active_member.end_turn()


@dataclass(kw_only=True)
class SoloTeam(Team):
    prompt: str | Path = Path("agent.jinja")

    def __repr__(self) -> str:
        return super().__repr__()

    def __hash__(self) -> int:
        return super().__hash__()

    def __post_init__(self):
        if len(self.members) != 1:
            raise ValueError("SoloTeam must have exactly one agent")
        super().__post_init__()

    def get_delegates(self) -> list[Actor]:
        return []

    def get_prompt(self) -> str:
        return self.members[0].get_prompt()


@dataclass(kw_only=True)
class Swarm(Team):
    """
    A swarm is a team that permits all agents to delegate to each other.
    """

    instructions: str | None = None

    description: str | None = "A team of agents that can delegate to each other."

    def __repr__(self) -> str:
        return super().__repr__()

    def __hash__(self) -> int:
        return super().__hash__()

    def get_delegates(self) -> list[Actor]:
        delegates = self.active_member.get_delegates()
        if delegates is None:
            return [a for a in self.members if a is not self.active_member]
        else:
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
        index = self.members.index(self.active_member)
        self.active_member = self.members[(index + 1) % len(self.members)]
        super().start_turn()


@dataclass(kw_only=True)
class RandomTeam(Team):
    description: str | None = "A team of agents that randomly selects an agent to act."

    def __repr__(self) -> str:
        return super().__repr__()

    def __hash__(self) -> int:
        return super().__hash__()

    def start_turn(self):
        self.set_active_agent(random.choice(self.members))
        super().start_turn()
