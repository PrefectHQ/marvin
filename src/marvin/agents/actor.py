import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pydantic_ai

import marvin
from marvin.prompts import Template


@dataclass(kw_only=True)
class Actor:
    instructions: str | None = field(
        default=None, metadata={"description": "Instructions for the actor"}
    )

    id: uuid.UUID = field(
        default_factory=uuid.uuid4,
        metadata={"description": "Unique identifier for this actor"},
    )

    prompt: str | Path

    def get_delegates(self) -> list["Actor"] | None:
        return None

    def get_agentlet(
        self,
        result_types: list[type],
        tools: list[Callable[..., Any]] | None = None,
        **kwargs,
    ) -> pydantic_ai.Agent[Any, Any]:
        raise NotImplementedError("Subclass must implement get_agent")

    def start_turn(self):
        pass

    def end_turn(self):
        pass

    def get_tools(self) -> list[Callable[..., Any]]:
        return []

    def get_end_turn_tools(self) -> list[type["marvin.engine.end_turn_tools.EndTurn"]]:
        return []

    def get_prompt(self) -> str:
        return Template(source=self.prompt).render()
