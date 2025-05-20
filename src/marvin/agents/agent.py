"""Agents for Marvin.

An Agent is an entity that can process tasks and maintain state across interactions.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence, TypeVar

import pydantic_ai
from pydantic_ai.mcp import MCPServer
from pydantic_ai.models import KnownModelName, Model, ModelSettings
from pydantic_ai.result import ToolOutput
from pydantic_ai.tools import Tool

import marvin

# from marvin._internal.integrations.fastmcp import ( # Commented out direct import
#     _pydantic_ai_mcp_server_from_fastmcp_server,
# )
from marvin._internal.integrations.mcp import discover_mcp_tools
from marvin.agents.actor import Actor
from marvin.agents.names import AGENT_NAMES
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.utilities.logging import get_logger
from marvin.utilities.tools import wrap_tool_errors
from marvin.utilities.types import issubclass_safe

logger = get_logger(__name__)
T = TypeVar("T")

# Attempt to import FastMCP and its converter for optional dependency handling
_FastMCPServerType = None
_fastmcp_converter = None
try:
    from fastmcp.server import FastMCP as FastMCPServer

    _FastMCPServerType = FastMCPServer
    from marvin._internal.integrations.fastmcp import (
        _pydantic_ai_mcp_server_from_fastmcp_server,
    )

    _fastmcp_converter = _pydantic_ai_mcp_server_from_fastmcp_server
except ImportError:
    logger.debug(
        "fastmcp extra not installed. To use FastMCP servers with Marvin, "
        "install with `pip install marvin[mcp]` or `uv pip install marvin[mcp]`."
    )

if TYPE_CHECKING:
    from marvin.engine.end_turn import EndTurn
    from marvin.engine.events import Event
    from marvin.handlers.handlers import AsyncHandler, Handler


async def handle_event(
    event: "Event", handlers: list["Handler | AsyncHandler"] | None = None
):
    """Handle an event by passing it to all registered handlers."""
    for handler in handlers or []:
        if isinstance(handler, AsyncHandler):
            await handler._handle(event)
        else:
            handler._handle(event)


@dataclass(kw_only=True)
class Agent(Actor):
    """An agent that can process tasks and maintain state."""

    name: str = field(
        default_factory=lambda: random.choice(AGENT_NAMES),
        metadata={"description": "Name of the agent"},
        kw_only=False,
    )

    tools: list[Callable[..., Any]] = field(
        default_factory=lambda: [],
        metadata={"description": "List of tools available to the agent"},
    )

    memories: list[Memory] = field(
        default_factory=lambda: [],
        metadata={"description": "List of memory modules available to the agent"},
    )

    mcp_servers: list[Any] = field(
        default_factory=lambda: [],
        metadata={"description": "List of MCP servers available to the agent"},
        repr=False,
    )

    model: KnownModelName | Model | None = field(
        default=None,
        metadata={
            "description": "The language model configuration for the agent."
            " Can be a known model name, a Pydantic AI Model instance,"
            " or None to use the default."
        },
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

    def get_mcp_servers(self) -> list[MCPServer]:
        converted_servers: list[MCPServer] = []
        for server_instance in self.mcp_servers:
            if (
                _FastMCPServerType is not None
                and _fastmcp_converter is not None
                and isinstance(server_instance, _FastMCPServerType)
            ):
                converted_servers.append(_fastmcp_converter(server_instance))
            elif isinstance(server_instance, MCPServer):
                converted_servers.append(server_instance)
            elif (
                _FastMCPServerType is None
                and hasattr(server_instance, "_mcp_server")
                and type(server_instance).__name__ == "FastMCP"
            ):  # Heuristic for when FastMCP is passed but not importable at top level
                logger.warning(
                    "FastMCP server instance passed, but marvin[mcp] extra seems not to be fully available for type checking. "
                    "Attempting to proceed, but this may indicate an incomplete installation or environment issue."
                )
                # This case is tricky; ideally, the top-level import should succeed if FastMCP is usable.
                # If we reach here, it means FastMCP was importable where the object was created but not in agent.py's top level.
                # This might occur in complex setups, but we should rely on the try-except block for typical cases.
                # For now, we can't convert it without _fastmcp_converter.
                # So, we log a more specific warning if the primary check fails but it looks like a FastMCP server.
                logger.error(
                    f"Encountered an object that appears to be a FastMCP server ({type(server_instance)}), "
                    "but the `fastmcp` integration is not available. Please install `marvin[mcp]`."
                )

            else:
                logger.warning(
                    f"Unexpected type in mcp_servers list: {type(server_instance)}.\n"
                    f"Expected FastMCPServer (if marvin[mcp] is installed) or pydantic_ai.mcp.MCPServer."
                )
        return converted_servers

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
        tools: Sequence[Callable[..., Any]],
        end_turn_tools: Sequence["EndTurn"],
        active_mcp_servers: list[MCPServer] | None = None,
    ) -> pydantic_ai.Agent[Any, Any]:
        import marvin.engine.orchestrator
        from marvin.engine.end_turn import EndTurn

        # --- Separate standard tools and EndTurn tools --- #
        all_potential_items = (
            list(tools)
            + self.get_tools()
            + list(end_turn_tools)
            + self.get_end_turn_tools()
        )
        marvin_tool_callables: list[Callable[..., Any]] = []
        final_end_turn_defs: list[type[EndTurn] | EndTurn] = []
        processed_ids: set[int] = set()
        for item in all_potential_items:
            item_id = id(item)
            if item_id in processed_ids:
                continue
            processed_ids.add(item_id)
            if issubclass_safe(item, EndTurn):
                final_end_turn_defs.append(item)
            elif isinstance(item, EndTurn):
                final_end_turn_defs.append(item)
            elif callable(item):
                marvin_tool_callables.append(item)
            else:
                logger.warning(f"Ignoring non-callable, non-EndTurn item: {item}")

        unique_marvin_tools = [wrap_tool_errors(tool) for tool in marvin_tool_callables]

        mcp_tool_instances: list[Tool] = []
        if active_mcp_servers:
            orchestrator = marvin.engine.orchestrator.get_current_orchestrator()
            mcp_tool_instances = await discover_mcp_tools(
                mcp_servers=active_mcp_servers,
                orchestrator=orchestrator,
            )

        combined_tools: list[Any] = unique_marvin_tools + mcp_tool_instances

        tool_output_name = "EndTurn"
        tool_output_description = "Ends the current turn."
        if len(final_end_turn_defs) == 1:
            output_type_for_tool_output = final_end_turn_defs[0]
            tool_output_name = getattr(
                output_type_for_tool_output, "__name__", tool_output_name
            )
        else:
            # Use None if zero or multiple EndTurn tools are present
            # This avoids schema issues but might prevent multi-turn scenarios?
            # TODO: Revisit handling of multiple EndTurn tools / Union[EndTurn]
            output_type_for_tool_output = type(None)
            if len(final_end_turn_defs) > 1:
                logger.warning(
                    "Multiple EndTurn tools detected, output validation might be limited."
                )

        final_tool_output = ToolOutput(
            type_=output_type_for_tool_output,
            name=tool_output_name,
            description=tool_output_description,
        )

        agent_kwargs = {
            "model": self.get_model(),
            "model_settings": self.get_model_settings(),
            "output_type": final_tool_output,  # Use the constructed ToolOutput
            "name": self.name,
        }

        if combined_tools:
            agent_kwargs["tools"] = combined_tools

        if active_mcp_servers:
            agent_kwargs["mcp_servers"] = active_mcp_servers

        agentlet = pydantic_ai.Agent[Any, Any](**agent_kwargs)

        # for internal use
        agentlet._marvin_tools = combined_tools
        agentlet._marvin_end_turn_tools = final_end_turn_defs  # Store original defs

        return agentlet

    def get_prompt(self) -> str:
        return Template(source=self.prompt).render(agent=self)
