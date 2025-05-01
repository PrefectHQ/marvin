"""Agents for Marvin.

An Agent is an entity that can process tasks and maintain state across interactions.
"""

import inspect
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence, TypeVar, Union
from unittest.mock import MagicMock

import pydantic_ai
from mcp.types import CallToolResult
from pydantic_ai.mcp import MCPServer
from pydantic_ai.models import KnownModelName, Model, ModelSettings
from pydantic_ai.result import ToolOutput
from pydantic_ai.tools import Tool, ToolDefinition

import marvin
from marvin.agents.actor import Actor
from marvin.agents.names import AGENT_NAMES
from marvin.engine.events import ToolCallEvent, ToolResultEvent
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.utilities.logging import get_logger
from marvin.utilities.tools import wrap_tool_errors
from marvin.utilities.types import issubclass_safe

logger = get_logger(__name__)
T = TypeVar("T")

if TYPE_CHECKING:
    # Needed for type hint in wrapper
    # from marvin.engine.orchestrator import Orchestrator # Already hinted via string
    # Import module for type hint resolution
    import marvin.engine.orchestrator
    from marvin.engine.end_turn import EndTurn
    from marvin.engine.events import Event
    from marvin.handlers.handlers import AsyncHandler, Handler


async def handle_event(
    event: "Event", handlers: list["Handler | AsyncHandler"] | None = None
):
    """Handle an event by passing it to all registered handlers."""
    orchestrator = marvin.engine.orchestrator.get_current_orchestrator()
    if orchestrator:
        await orchestrator.handle_event(event)
    else:
        logger.warning(f"No orchestrator found to handle event: {type(event).__name__}")


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

    mcp_servers: list[MCPServer] = field(
        default_factory=list,
        metadata={"description": "List of MCP servers available to the agent"},
        repr=False,
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

    def get_mcp_servers(self) -> list[MCPServer]:
        return self.mcp_servers

    def get_model_settings(self) -> ModelSettings:
        defaults: ModelSettings = {}
        if marvin.settings.agent_temperature is not None:
            defaults["temperature"] = marvin.settings.agent_temperature
        return defaults | self.model_settings

    async def get_agentlet(
        self,
        tools: Sequence[Callable[..., Any]],
        end_turn_tools: Sequence["EndTurn"],
        active_mcp_servers: list[MCPServer] | None = None,
    ) -> pydantic_ai.Agent[Any, Any]:
        import marvin.engine.orchestrator
        from marvin.engine.end_turn import EndTurn

        all_potential_tools = (
            list(tools)
            + self.get_tools()
            + list(end_turn_tools)
            + self.get_end_turn_tools()
        )

        cleaned_marvin_tools: list[Callable[..., Any]] = []
        final_end_turn_tool_defs: list[type[EndTurn] | EndTurn] = []
        processed_items: set[int] = set()

        for item in all_potential_tools:
            item_id = id(item)
            if item_id in processed_items:
                continue
            processed_items.add(item_id)

            if issubclass_safe(item, EndTurn):
                final_end_turn_tool_defs.append(item)
            elif isinstance(item, EndTurn):
                final_end_turn_tool_defs.append(item)
            elif callable(item):
                cleaned_marvin_tools.append(item)
            else:
                logger.warning(f"Ignoring non-callable, non-EndTurn item: {item}")
        # Prepare Marvin tools
        marvin_tools_for_pydantic: list[Tool] = [
            Tool(wrap_tool_errors(tool)) for tool in cleaned_marvin_tools
        ]

        # Prepare MCP tools
        mcp_tools_for_pydantic: list[Tool] = []
        if active_mcp_servers:
            orchestrator = marvin.engine.orchestrator.get_current_orchestrator()
            if not orchestrator:
                logger.warning("No active orchestrator found for MCP event handling.")

            for mcp_server in active_mcp_servers:
                if not getattr(mcp_server, "is_running", False):
                    logger.warning(
                        f"MCP Server {mcp_server} is not running, skipping tool loading."
                    )
                    continue
                try:
                    tool_defs: list[ToolDefinition] = await mcp_server.list_tools()
                except Exception as e:
                    logger.error(
                        f"Failed to list tools from {mcp_server}: {e}", exc_info=True
                    )
                    continue

                for tool_def in tool_defs:
                    # Define the execution wrapper
                    async def mcp_tool_wrapper(
                        # Capture loop variables
                        _mcp_server: MCPServer = mcp_server,
                        _tool_def: ToolDefinition = tool_def,
                        _actor: Actor = self,
                        _orchestrator: "marvin.engine.orchestrator.Orchestrator | None" = orchestrator,
                        **kwargs: Any,
                    ) -> Any:
                        # Create a placeholder tool object for the event
                        mock_tool_obj = MagicMock()
                        mock_tool_obj.name = _tool_def.name
                        mock_tool_obj.description = _tool_def.description
                        # Add schema if needed by handlers?
                        # mock_tool_obj.parameters_json_schema = _tool_def.parameters_json_schema

                        # Use new fields for ToolCallEvent
                        tool_call_event = ToolCallEvent(
                            actor=_actor,
                            tool=mock_tool_obj,
                            tool_name=_tool_def.name,
                            tool_input=kwargs,
                            tool_source="mcp",
                            # message and tool_call_id are omitted as they come later from pydantic-ai
                        )
                        # tool_call_event.tool_source = "mcp" # Source added in constructor now

                        if _orchestrator:
                            await _orchestrator.handle_event(tool_call_event)
                        else:
                            logger.warning(
                                f"No orchestrator to handle ToolCallEvent for MCP tool {_tool_def.name}"
                            )

                        logger.debug(
                            f"Calling MCP tool '{_tool_def.name}' via {type(_mcp_server).__name__}"
                        )
                        try:
                            result: CallToolResult = await _mcp_server.call_tool(
                                tool_name=_tool_def.name, arguments=kwargs
                            )
                            result_content = result.content

                            # Use new fields for ToolResultEvent
                            tool_result_event = ToolResultEvent(
                                actor=_actor,
                                tool=mock_tool_obj,
                                tool_name=_tool_def.name,
                                tool_result=result_content,
                                tool_source="mcp",
                                # message is omitted
                            )
                            # tool_result_event.tool_source = "mcp" # Source added in constructor now

                            if _orchestrator:
                                await _orchestrator.handle_event(tool_result_event)
                            else:
                                logger.warning(
                                    f"No orchestrator to handle ToolResultEvent for MCP tool {_tool_def.name}"
                                )

                            logger.debug(
                                f"MCP tool '{_tool_def.name}' returned result."
                            )
                            # Return the raw content expected by Pydantic AI
                            return result_content
                        except Exception as e:
                            logger.error(
                                f"Error calling MCP tool '{_tool_def.name}': {e}",
                                exc_info=True,
                            )
                            # TODO: Trigger specific Marvin error event?
                            return f"Error calling tool {_tool_def.name}: {e}"

                        return result_content

                    # Create a pydantic_ai.Tool object using the definition and wrapper
                    mcp_tool = Tool(  # type: ignore
                        func=mcp_tool_wrapper,  # The actual callable
                        name=tool_def.name,
                        description=tool_def.description,
                        parameters_json_schema=tool_def.parameters_json_schema,
                        takes_ctx=False,  # The wrapper handles context implicitly
                    )
                    mcp_tools_for_pydantic.append(mcp_tool)

        # Combine all tools for pydantic_ai.Agent
        all_tools = marvin_tools_for_pydantic + mcp_tools_for_pydantic

        # Define the output type based on EndTurn tools
        if not final_end_turn_tool_defs:
            # Default to EndTurn if none specific provided? Or raise error?
            # For now, let's default to the base EndTurn type.
            output_union = EndTurn
        elif len(final_end_turn_tool_defs) == 1:
            # If only one, use its type or the instance itself if already instantiated
            output_union = final_end_turn_tool_defs[0]
        else:
            # Create a Union of all provided EndTurn types/instances
            # Note: pydantic-ai might internally handle instances vs types in Union
            output_union = Union[tuple(final_end_turn_tool_defs)]

        # Create the pydantic_ai.Agent instance
        pydantic_agent = pydantic_ai.Agent[Any, Any](
            model=self.get_model(),  # type: ignore
            model_settings=self.get_model_settings(),  # type: ignore
            tools=all_tools,  # Pass combined list of Tool objects
            # Pass the Union of EndTurn types/instances to ToolOutput
            output_type=ToolOutput(type_=output_union),  # Use type_ arg
            mcp_servers=active_mcp_servers or [],
            name=self.name,
        )

        # Assign useful attributes (use underscore prefix for internal use)
        pydantic_agent._marvin_tools = cleaned_marvin_tools
        pydantic_agent._marvin_end_turn_tools = final_end_turn_tool_defs

        return pydantic_agent

    def get_prompt(self) -> str:
        return Template(source=self.prompt).render(agent=self)
