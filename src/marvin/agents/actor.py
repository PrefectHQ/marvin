import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pydantic_ai

import marvin
import marvin.utilities.asyncio
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.thread import Thread

if TYPE_CHECKING:
    from marvin.agents.team import Team
    from marvin.engine.end_turn import EndTurn


@dataclass(kw_only=True)
class Actor:
    id: str = field(
        default_factory=lambda: uuid.uuid4().hex[:8],
        metadata={"description": "Unique identifier for this actor"},
        # repr=False,
        init=False,
    )

    name: str = field(
        metadata={"description": "Name of the actor"},
    )

    instructions: str | None = field(
        default=None,
        metadata={"description": "Instructions for the actor, private to the actor."},
        repr=False,
    )

    description: str | None = field(
        default=None,
        metadata={"description": "Description of the actor, visible to other actors."},
        repr=False,
    )

    prompt: str | Path = field(repr=False)

    def __hash__(self) -> int:
        return hash(self.id)

    def get_delegates(self) -> list["Actor"] | None:
        """A list of actors that this actor can delegate to."""
        return None

    def get_agentlet(
        self,
        result_types: list[type],
        tools: list[Callable[..., Any]] | None = None,
        **kwargs: Any,
    ) -> pydantic_ai.Agent[Any, Any]:
        raise NotImplementedError("Subclass must implement get_agentlet")

    def start_turn(self):
        """Called when the actor starts its turn."""

    def end_turn(self):
        """Called when the actor ends its turn."""

    def get_tools(self) -> list[Callable[..., Any]]:
        """A list of tools that this actor can use during its turn."""
        return []

    def get_memories(self) -> list[Memory]:
        """A list of memories that this actor can use during its turn."""
        return []

    def get_end_turn_tools(self) -> list[type["EndTurn"]]:
        """A list of `EndTurn` tools that this actor can use to end its turn."""
        return []

    def get_prompt(self) -> str:
        return Template(source=self.prompt).render()

    def friendly_name(self) -> str:
        return f'{self.__class__.__name__} "{self.name}" ({self.id})'

    async def run_async(
        self,
        instructions: str,
        thread: Thread | str | None = None,
        raise_on_failure: bool = True,
    ) -> Any:
        return await marvin.run_async(
            instructions,
            agents=[self],
            thread=thread,
            raise_on_failure=raise_on_failure,
        )

    def run(
        self,
        instructions: str,
        thread: Thread | str | None = None,
        raise_on_failure: bool = True,
    ) -> Any:
        return marvin.utilities.asyncio.run_sync(
            self.run_async(instructions, thread, raise_on_failure),
        )

    async def say_async(
        self,
        message: str,
        instructions: str | None = None,
        thread: Thread | str | None = None,
    ):
        """Responds to a user message in a conversational way."""
        return await marvin.say_async(
            message=message,
            instructions=instructions,
            agent=self,
            thread=thread,
        )

    def say(
        self,
        message: str,
        instructions: str | None = None,
        thread: Thread | str | None = None,
    ):
        """Responds to a user message in a conversational way."""
        return marvin.utilities.asyncio.run_sync(
            self.say_async(message=message, instructions=instructions, thread=thread),
        )

    def as_team(self) -> "Team":
        raise NotImplementedError(
            "Subclass must implement as_team in order to be properly orchestrated.",
        )
