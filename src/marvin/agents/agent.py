"""Agents for Marvin.

An Agent is an entity that can process tasks and maintain state across interactions.
"""

import inspect
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, Union

import pydantic_ai
from pydantic_ai.models import KnownModelName, Model, ModelSettings

import marvin
from marvin.agents.actor import Actor
from marvin.agents.names import AGENT_NAMES
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.utilities.logging import get_logger
from marvin.utilities.tools import wrap_tool_errors
from marvin.utilities.types import issubclass_safe

logger = get_logger(__name__)
T = TypeVar("T")

if TYPE_CHECKING:
    from marvin.engine.end_turn import EndTurn
    from marvin.engine.events import Event
    from marvin.engine.handlers import AsyncHandler, Handler


async def handle_event(
    event: "Event", handlers: list["Handler | AsyncHandler"] | None = None
):
    """Handle an event by passing it to all registered handlers."""
    for handler in handlers or []:
        if isinstance(handler, AsyncHandler):
            await handler.handle(event)
        else:
            handler.handle(event)


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
            "description": inspect.cleandoc("""
                The model to use for the agent. If not provided,
                the default model will be used. A compatible string
                can be passed to automatically retrieve the model.
                """),
        },
        repr=False,
    )

    model_settings: ModelSettings = field(
        default_factory=ModelSettings,
        metadata={"description": "Settings to pass to the model"},
        repr=False,
    )

    prompt: str | Path = field(
        default=Path("agent.jinja"),
        metadata={"description": "Template for the agent's prompt"},
        repr=False,
    )

    def __hash__(self) -> int:
        return super().__hash__()

    def get_model(self) -> Model | KnownModelName:
        return self.model or marvin.defaults.model

    def get_tools(self) -> list[Callable[..., Any]]:
        tools = self.tools + [t for m in self.memories for t in m.get_tools()]
        return tools

    def get_memories(self) -> list[Memory]:
        return list(self.memories)

    def get_model_settings(self) -> ModelSettings:
        defaults: ModelSettings = {}
        if marvin.settings.agent_temperature is not None:
            defaults["temperature"] = marvin.settings.agent_temperature
        return defaults | self.model_settings

    def _determine_result_type(self, end_turn_tools: list[Any]) -> type:
        # Simplified logic: if exactly one end-turn tool, use its type,
        # otherwise return a Union of all available end-turn types.
        if len(end_turn_tools) == 1:
            return end_turn_tools[0]
        else:
            from typing import Union

            return Union[tuple(end_turn_tools)]

    async def get_agentlet(
        self,
        tools: list[Callable[..., Any]],
        end_turn_tools: list["EndTurn"],
    ) -> pydantic_ai.Agent[Any, Any]:
        """
        A full streaming iterator over an agent's run.

        This method creates an agentlet (a pydantic_ai.Agent instance) and uses its
        .iter() method to obtain nodes. For nodes that support streaming (model requests or
        handle responses), it opens the stream and yields each event. Other nodes (e.g. the
        initial user prompt or the final End node) are yielded directly.
        """

        from marvin.engine.end_turn import EndTurn

        tools = tools + self.get_tools()
        end_turn_tools = end_turn_tools + self.get_end_turn_tools()

        # if any tools are actually EndTurn classes, remove them from tools and
        # add them to end turn tools
        for t in tools:
            if issubclass_safe(t, EndTurn):
                tools.remove(t)
                end_turn_tools.append(t)

        if not end_turn_tools:
            result_type = [EndTurn]

        if len(end_turn_tools) == 1:
            result_type = end_turn_tools[0]
            result_tool_name = result_type.__name__
        else:
            result_type = Union[tuple(end_turn_tools)]
            result_tool_name = "EndTurn"

        tools = [wrap_tool_errors(tool) for tool in tools or []]

        agentlet = pydantic_ai.Agent[Any, result_type](  # type: ignore
            model=self.get_model(),
            result_type=result_type,
            tools=tools,
            model_settings=self.get_model_settings(),
            end_strategy="exhaustive",
            result_tool_name=result_tool_name or "EndTurn",
            result_tool_description="This tool will end your turn. You may only use one EndTurn tool per turn.",
            retries=marvin.settings.agent_retries,
        )
        # new fields
        agentlet._marvin_tools = tools
        agentlet._marvin_end_turn_tools = end_turn_tools
        return agentlet

    def get_prompt(self) -> str:
        return Template(source=self.prompt).render(agent=self)


def get_agentlet(
    agent: Agent,
    result_type: type,
    tools: list[Callable[..., Any]] | None = None,
    end_turn_tools: list["EndTurn"] | None = None,
    result_tool_name: str | None = None,
) -> pydantic_ai.Agent[Any, Any]:
    """Create a Pydantic AI agent with the specified configuration.

    Args:
        result_type: The expected return type of the agent
        model: The model to use for the agent
        model_settings: Settings to pass to the model
        tools: Optional list of tools available to the agent
        handlers: Optional list of event handlers
        result_tool_name: Optional name for the result tool
        actor: Optional actor instance for event handling
    """

    tools = [wrap_tool_errors(tool) for tool in tools or []]

    agentlet = pydantic_ai.Agent[Any, result_type](  # type: ignore
        model=agent.get_model(),
        result_type=result_type,
        tools=tools,
        model_settings=agent.get_model_settings(),
        end_strategy="exhaustive",
        result_tool_name=result_tool_name or "EndTurn",
        result_tool_description="This tool will end your turn. You may only use one EndTurn tool per turn.",
        retries=marvin.settings.agent_retries,
        original_tools=tools,
        original_end_turn_tools=end_turn_tools,
    )

    return agentlet
