"""
Module for integrating Model Context Protocol (MCP) servers with Marvin.

**Status:** Experimental
"""

import asyncio
import uuid
from functools import partial
from typing import TYPE_CHECKING, Any, Coroutine

from mcp.types import CallToolResult
from pydantic_ai.mcp import MCPServer
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.tools import Tool, ToolDefinition

import marvin
from marvin.agents.actor import Actor
from marvin.engine.events import ToolCallEvent, ToolResultEvent
from marvin.utilities.logging import get_logger

if TYPE_CHECKING:
    import marvin.engine.orchestrator

logger = get_logger(__name__)


class _MCPToolAdapter:
    _tool_def: ToolDefinition
    name: str
    description: str

    def __init__(self, tool_definition: ToolDefinition):
        self._tool_def = tool_definition
        self.name = tool_definition.name
        self.description = tool_definition.description

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        return f"MCPToolAdapter for '{self.name}'. Call via the appropriate MCPServer."

    def __repr__(self) -> str:
        desc_snippet = (
            f"{self.description[:50]}..."
            if len(self.description) > 50
            else self.description
        )
        return f"MCPToolAdapter(name='{self.name}', description='{desc_snippet}')"


async def _mcp_tool_wrapper(
    *,
    _mcp_server: MCPServer,
    _tool_def: ToolDefinition,
    _actor: Actor,
    _orchestrator: "marvin.engine.orchestrator.Orchestrator | None",
    **kwargs: Any,
) -> Any:
    if not _orchestrator:
        raise RuntimeError("orchestrator not found, this is unexpected")

    tool_call_id = f"mcp-{uuid.uuid4()}"
    tool_name = _tool_def.name

    mcp_tool_adapter = _MCPToolAdapter(tool_definition=_tool_def)

    await _orchestrator.handle_event(
        ToolCallEvent(
            actor=_actor,
            message=ToolCallPart(
                tool_name=tool_name,
                args=kwargs,
                tool_call_id=tool_call_id,
            ),
            tool_call_id=tool_call_id,
            tool=mcp_tool_adapter,
        )
    )

    logger.debug(f"Calling MCP tool '{tool_name}' via {type(_mcp_server).__name__}")
    try:
        result: CallToolResult = await _mcp_server.call_tool(
            tool_name=tool_name, arguments=kwargs
        )
        result_content = result.content

        await _orchestrator.handle_event(
            ToolResultEvent(
                message=ToolReturnPart(
                    tool_name=tool_name,
                    content=result_content,
                    tool_call_id=tool_call_id,
                ),
            )
        )

        logger.debug(f"MCP tool '{tool_name}' returned result: {result_content!r}")
        return result_content
    except Exception as e:
        logger.error(f"Error calling MCP tool '{tool_name}': {e}", exc_info=True)
        error_content = f"Error calling tool {tool_name}: {e}"
        try:
            await _orchestrator.handle_event(
                ToolResultEvent(
                    message=ToolReturnPart(
                        tool_name=tool_name,
                        content=error_content,
                        tool_call_id=tool_call_id,
                    )
                )
            )
        except Exception as e_inner:
            logger.error(
                f"Failed to create/send error ToolResultEvent for {tool_name}: {e_inner}",
                exc_info=True,
            )

        return error_content


async def discover_mcp_tools(
    mcp_servers: list[MCPServer],
    actor: Actor,
    orchestrator: "marvin.engine.orchestrator.Orchestrator | None",
) -> list[Tool]:
    mcp_tools: list[Tool] = []
    if not mcp_servers:
        return mcp_tools

    discovery_tasks: list[Coroutine[Any, Any, list[ToolDefinition]]] = []
    server_map: dict[int, MCPServer] = {}

    for i, server in enumerate(mcp_servers):
        if not getattr(server, "is_running", False):
            logger.warning(
                f"MCP Server {server!r} is not marked as running, skipping tool discovery."
            )
            continue
        discovery_tasks.append(server.list_tools())
        server_map[i] = server

    if not discovery_tasks:
        return mcp_tools

    tool_definition_results: list[
        list[ToolDefinition] | BaseException
    ] = await asyncio.gather(*discovery_tasks, return_exceptions=True)

    for i, result in enumerate(tool_definition_results):
        server = server_map[i]
        if isinstance(result, BaseException):
            logger.error(
                f"Failed to list tools from {server!r}: {result}", exc_info=result
            )
            continue

        tool_defs: list[ToolDefinition] = result
        logger.debug(
            f"Discovered {len(tool_defs)} tool{'' if len(tool_defs) == 1 else 's'} from {server!r}"
        )
        for tool_def in tool_defs:
            wrapped_func = partial(
                _mcp_tool_wrapper,
                _mcp_server=server,
                _tool_def=tool_def,
                _actor=actor,
                _orchestrator=orchestrator,
            )

            # Use a default argument to capture the current value of wrapped_func
            # This prevents the closure from capturing the loop variable by reference.
            async def async_wrapped_func_fixed(
                _bound_partial=wrapped_func,  # No type hint here for Pydantic inspection
                **kwargs: Any,
            ) -> Any:
                # Call the captured partial, not the loop variable
                return await _bound_partial(**kwargs)

            mcp_tools.append(
                Tool(
                    function=async_wrapped_func_fixed,  # Use the fixed function
                    name=tool_def.name,
                    description=tool_def.description,
                    takes_ctx=False,
                )
            )

    return mcp_tools
