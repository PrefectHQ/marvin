import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Sequence, TypeVar

import pydantic_ai
from pydantic_ai.agent import AgentRunResult

import marvin
import marvin.utilities.asyncio
from marvin.engine.llm import Message
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.thread import Thread

if TYPE_CHECKING:
    from marvin.engine.end_turn import EndTurn
    from marvin.engine.handlers import AsyncHandler, Handler
    from marvin.engine.orchestrator import Orchestrator
T = TypeVar("T")
# Global context var for current actor
_current_actor: ContextVar[Optional["Actor"]] = ContextVar(
    "current_actor",
    default=None,
)


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

    _tokens: list[Any] = field(default_factory=list, init=False, repr=False)

    def __hash__(self) -> int:
        return hash(self.id)

    def __enter__(self):
        """Set this actor as the current actor in context."""
        token = _current_actor.set(self)
        self._tokens.append(token)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        """Reset the current actor in context."""
        if self._tokens:  # Only reset if we have tokens
            _current_actor.reset(self._tokens.pop())

    @classmethod
    def get_current(cls) -> Optional["Actor"]:
        """Get the current actor from context."""
        return _current_actor.get()

    @abstractmethod
    async def get_agentlet(
        self,
        messages: list[Message],
        tools: Sequence[Callable[..., Any]],
        end_turn_tools: Sequence["EndTurn"],
    ) -> pydantic_ai.Agent[Any, Any]:
        raise NotImplementedError("Actor subclasses must implement _run")

    async def start_turn(self, orchestrator: "Orchestrator"):
        """Called when the actor starts its turn."""
        pass

    async def end_turn(self, orchestrator: "Orchestrator", result: AgentRunResult):
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
        result_type: type[T] = str,
        tools: list[Callable[..., Any]] = [],
        thread: Thread | str | None = None,
        handlers: list["Handler | AsyncHandler"] | None = None,
        raise_on_failure: bool = True,
        **kwargs: Any,
    ) -> Any:
        return await marvin.run_async(
            instructions=instructions,
            result_type=result_type,
            tools=tools,
            agents=[self],
            thread=thread,
            raise_on_failure=raise_on_failure,
            handlers=handlers,
            **kwargs,
        )

    def run(
        self,
        instructions: str,
        result_type: type[T] = str,
        tools: list[Callable[..., Any]] = [],
        thread: Thread | str | None = None,
        handlers: list["Handler | AsyncHandler"] | None = None,
        raise_on_failure: bool = True,
        **kwargs: Any,
    ) -> Any:
        return marvin.utilities.asyncio.run_sync(
            self.run_async(
                instructions=instructions,
                result_type=result_type,
                tools=tools,
                thread=thread,
                handlers=handlers,
                raise_on_failure=raise_on_failure,
                **kwargs,
            ),
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


def get_current_actor() -> Actor | None:
    """Get the currently active actor from context.

    Returns:
        The current Actor instance or None if no actor is active.
    """
    return Actor.get_current()
