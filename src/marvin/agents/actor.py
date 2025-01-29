import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Sequence

from pydantic_ai.result import RunResult

import marvin
import marvin.utilities.asyncio
from marvin.engine.llm import Message
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.thread import Thread

if TYPE_CHECKING:
    from marvin.agents.team import Team
    from marvin.engine.end_turn import EndTurn
    from marvin.engine.orchestrator import Orchestrator


@dataclass(kw_only=True)
class Actor(ABC):
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

    @abstractmethod
    async def _run(
        self,
        messages: list[Message],
        tools: Sequence[Callable[..., Any]],
        end_turn_tools: Sequence["EndTurn"],
    ) -> RunResult:
        raise NotImplementedError("Actor subclasses must implement _run")

    async def start_turn(self, orchestrator: "Orchestrator"):
        """Called when the actor starts its turn."""
        pass

    async def end_turn(self, orchestrator: "Orchestrator", result: RunResult):
        """Called when the actor ends its turn."""
        pass

    def get_tools(self) -> list[Callable[..., Any]]:
        """A list of tools that this actor can use during its turn."""
        return []

    def get_end_turn_tools(self) -> list["EndTurn"]:
        """A list of `EndTurn` tools that this actor can use to end its turn."""
        return []

    def get_memories(self) -> list[Memory]:
        """A list of memories that this actor can use during its turn."""
        return []

    def get_prompt(self) -> str:
        return Template(source=self.prompt).render(actor=self)

    def friendly_name(self, verbose: bool = True) -> str:
        if verbose:
            return f'{self.__class__.__name__} "{self.name}" ({self.id})'
        else:
            return self.name

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
