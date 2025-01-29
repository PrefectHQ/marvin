import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from pydantic_ai.result import RunResult

from marvin.agents.actor import Actor
from marvin.agents.names import TEAM_NAMES
from marvin.memory.memory import Memory
from marvin.prompts import Template

if TYPE_CHECKING:
    from marvin.engine.end_turn import EndTurn
    from marvin.engine.llm import Message
    from marvin.engine.orchestrator import Orchestrator


@dataclass(kw_only=True)
class Team(Actor):
    """A team is a container that maintains state for a group of agents."""

    members: list[Actor]
    active_member: Actor = field(init=False)

    name: str = field(
        default_factory=lambda: random.choice(TEAM_NAMES),
        metadata={"description": "Name of the team"},
    )

    prompt: str | Path = field(
        default=Path("team.jinja"),
        metadata={"description": "Template for the team's prompt"},
    )

    def __post_init__(self):
        if not self.members:
            raise ValueError("Team must have at least one member")
        self.active_member = self.members[0]

    async def start_turn(self, orchestrator: "Orchestrator"):
        await self.active_member.start_turn(orchestrator=orchestrator)

    async def end_turn(
        self,
        orchestrator: "Orchestrator",
        result: RunResult,
    ):
        await self.active_member.end_turn(result=result, orchestrator=orchestrator)

    def get_prompt(self) -> str:
        return Template(source=self.prompt).render(team=self)

    def get_memories(self) -> list[Memory]:
        return self.active_member.get_memories()

    async def _run(
        self,
        messages: list["Message"],
        tools: list[Callable[..., Any]],
        end_turn_tools: list["EndTurn"],
    ) -> RunResult:
        return await self.active_member._run(
            messages=messages,
            tools=self.get_tools() + tools,
            end_turn_tools=self.get_end_turn_tools() + end_turn_tools,
        )

    def friendly_name(self, verbose: bool = True) -> str:
        return self.active_member.friendly_name(verbose=verbose)


@dataclass(kw_only=True)
class Swarm(Team):
    """A swarm is a team that permits all agents to delegate to each other."""

    def get_end_turn_tools(self) -> list["EndTurn"]:
        from marvin.engine.end_turn import create_delegate_to_actor

        end_turn_tools = super().get_end_turn_tools()

        for member in self.members:
            if member is not self.active_member:
                end_turn_tools.append(
                    create_delegate_to_actor(delegate_actor=member, team=self)
                )

        return end_turn_tools


# @dataclass(kw_only=True)
# class Team(Actor):
#     members: list[Actor]
#     name: str = field(
#         default_factory=lambda: random.choice(TEAM_NAMES),
#         metadata={"description": "Name of the team"},
#     )

#     prompt: str | Path = field(
#         default=Path("team.jinja"),
#         metadata={"description": "Template for the team's prompt"},
#     )

#     allow_message_posting: bool = field(
#         default=True,
#         metadata={
#             "description": "Whether to allow the team to post messages to the thread",
#         },
#     )

#     active_member: Actor = field(init=False)

#     def __hash__(self) -> int:
#         return super().__hash__()

#     def __repr__(self) -> str:
#         return f"{self.__class__.__name__}(name={self.name!r}, agents={[a.name for a in self.members]})"

#     def get_delegates(self) -> list[Actor]:
#         """
#         By default, agents can delegate only to pre-defined agents. If no delegates are defined,
#         none are returned.
#         """
#         delegates = self.active_member.get_delegates()
#         return delegates or []

#     def __post_init__(self):
#         self.agents_by_id = {a.id: a for a in self.members}
#         self.active_member = self.members[0]

#     def get_agentlet(
#         self,
#         result_types: list[type],
#         tools: list[Callable[..., Any]] | None = None,
#         **kwargs: Any,
#     ) -> pydantic_ai.Agent[Any, Any]:
#         return self.active_member.get_agentlet(
#             tools=self.get_end_turn_tools() + (tools or []),
#             result_types=result_types,
#             **kwargs,
#         )

#     def get_prompt(self) -> str:
#         return Template(source=self.prompt).render(team=self)

#     def get_end_turn_tools(self) -> list[type["EndTurn"]]:
#         return []

#     def start_turn(self):
#         if self.active_member:
#             self.active_member.start_turn()

#     def end_turn(self):
#         if self.active_member:
#             self.active_member.end_turn()

#     def contains(self, agent: Agent) -> bool:
#         for member in self.members:
#             if member is agent:
#                 return True
#             elif isinstance(member, Team) and member.contains(agent):
#                 return True
#         return False


# @dataclass(kw_only=True)
# class Swarm(Team):
#     """A swarm is a team that permits all agents to delegate to each other."""

#     instructions: str | None = None

#     description: str | None = "A team of agents that can delegate to each other."

#     def __repr__(self) -> str:
#         return super().__repr__()

#     def __hash__(self) -> int:
#         return super().__hash__()

#     def get_delegates(self) -> list[Actor]:
#         delegates = self.active_member.get_delegates()
#         if delegates is None:
#             return [a for a in self.members if a is not self.active_member]
#         return delegates

#     def get_end_turn_tools(self) -> list[type["EndTurn"]]:
#         return [DelegateToAgent]


# @dataclass(kw_only=True)
# class RoundRobinTeam(Team):
#     description: str | None = "A team of agents that rotate turns."

#     def __repr__(self) -> str:
#         return super().__repr__()

#     def __hash__(self) -> int:
#         return super().__hash__()

#     def start_turn(self):
#         index = self.members.index(self.active_member)
#         self.active_member = self.members[(index + 1) % len(self.members)]
#         super().start_turn()


# @dataclass(kw_only=True)
# class RandomTeam(Team):
#     description: str | None = "A team of agents that randomly selects an agent to act."

#     def __repr__(self) -> str:
#         return super().__repr__()

#     def __hash__(self) -> int:
#         return super().__hash__()

#     def start_turn(self):
#         self.active_member = random.choice(self.members)
#         super().start_turn()
