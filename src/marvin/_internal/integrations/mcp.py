"""
Module for integrating Model Context Protocol (MCP) servers with Marvin.

**Status:** Experimental
"""

import asyncio
import uuid  # Added for tool_call_id
from functools import partial
from typing import TYPE_CHECKING, Any, Coroutine
from unittest.mock import MagicMock

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


async def _mcp_tool_wrapper(
    *,
    _mcp_server: MCPServer,
    _tool_def: ToolDefinition,
    _actor: Actor,
    _orchestrator: "marvin.engine.orchestrator.Orchestrator | None",
    **kwargs: Any,
) -> Any:
    """Wraps an MCP tool call to integrate with Marvin's event system."""
    tool_call_id = f"mcp-{uuid.uuid4()}"
    tool_name = _tool_def.name

    # Create a mock tool object for event reporting
    mock_tool_obj = MagicMock()
    mock_tool_obj.name = tool_name
    mock_tool_obj.description = _tool_def.description

    # --- Create ToolCallPart and ToolCallEvent --- #
    tool_call_part = ToolCallPart(
        tool_name=tool_name,
        args=kwargs,  # Pass the actual arguments received
        tool_call_id=tool_call_id,
    )
    tool_call_event = ToolCallEvent(
        actor=_actor,
        message=tool_call_part,
        tool_call_id=tool_call_id,
        tool=mock_tool_obj,  # Use the mock object
    )

    if _orchestrator:
        await _orchestrator.handle_event(tool_call_event)
    else:
        logger.warning(
            f"No orchestrator found to handle ToolCallEvent for MCP tool {tool_name}"
        )

    logger.debug(f"Calling MCP tool '{tool_name}' via {type(_mcp_server).__name__}")
    try:
        result: CallToolResult = await _mcp_server.call_tool(
            tool_name=tool_name, arguments=kwargs
        )
        result_content = result.content

        # --- Create ToolReturnPart and ToolResultEvent --- #
        tool_return_part = ToolReturnPart(
            tool_name=tool_name,
            content=result_content,
            tool_call_id=tool_call_id,
        )
        tool_result_event = ToolResultEvent(
            message=tool_return_part,
        )

        if _orchestrator:
            await _orchestrator.handle_event(tool_result_event)
        else:
            logger.warning(
                f"No orchestrator found to handle ToolResultEvent for MCP tool {tool_name}"
            )

        logger.debug(f"MCP tool '{tool_name}' returned result: {result_content!r}")
        return result_content
    except Exception as e:
        logger.error(f"Error calling MCP tool '{tool_name}': {e}", exc_info=True)
        # Attempt to create an error ToolReturnPart
        error_content = f"Error calling tool {tool_name}: {e}"
        try:
            tool_return_part = ToolReturnPart(
                tool_name=tool_name,
                content=error_content,
                tool_call_id=tool_call_id,
            )
            tool_result_event = ToolResultEvent(message=tool_return_part)
            if _orchestrator:
                await _orchestrator.handle_event(tool_result_event)
        except Exception as e_inner:
            logger.error(
                f"Failed to create/send error ToolResultEvent for {tool_name}: {e_inner}",
                exc_info=True,
            )

        # Return the error string for pydantic-ai
        return error_content


async def discover_mcp_tools(
    mcp_servers: list[MCPServer],
    actor: Actor,
    orchestrator: "marvin.engine.orchestrator.Orchestrator | None",
) -> list[Tool]:
    """Discovers tools from active MCP servers and wraps them for Marvin."""
    mcp_tools: list[Tool] = []
    if not mcp_servers:
        return mcp_tools

    discovery_tasks: list[Coroutine[Any, Any, list[ToolDefinition]]] = []
    server_map: dict[int, MCPServer] = {}

    for i, server in enumerate(mcp_servers):
        # Ensure server is running (best effort check)
        if not getattr(server, "is_running", False):
            logger.warning(
                f"MCP Server {server!r} is not marked as running, skipping tool discovery."
            )
            continue
        discovery_tasks.append(server.list_tools())
        server_map[i] = server  # Map task index back to server

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
        logger.debug(f"Discovered {len(tool_defs)} tools from {server!r}")
        for tool_def in tool_defs:
            # Create a partial function for the wrapper with context
            wrapped_func = partial(
                _mcp_tool_wrapper,
                _mcp_server=server,
                _tool_def=tool_def,
                _actor=actor,
                _orchestrator=orchestrator,
            )

            # Ensure the partial function has the correct async nature
            # Not strictly necessary as partial preserves it, but explicit
            async def async_wrapped_func(**kwargs: Any) -> Any:
                return await wrapped_func(**kwargs)

            # Create the pydantic_ai.Tool object
            # NOTE: parameters_json_schema is not passed to the constructor
            #       It's inferred internally by pydantic-ai based on the function signature
            mcp_tool = Tool(
                function=async_wrapped_func,
                name=tool_def.name,
                description=tool_def.description,
                takes_ctx=False,
            )
            mcp_tools.append(mcp_tool)

    logger.info(f"Discovered a total of {len(mcp_tools)} MCP tools.")
    return mcp_tools
