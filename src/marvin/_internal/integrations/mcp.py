"""
Experimental module for integrating Model Context Protocol (MCP) servers with Marvin.
"""

import asyncio
import os
import uuid
from contextlib import AsyncExitStack, asynccontextmanager
from functools import partial
from typing import TYPE_CHECKING, Any, AsyncIterator, Coroutine

from mcp.types import CallToolResult
from pydantic_ai.mcp import MCPServer, MCPServerStdio
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.tools import Tool, ToolDefinition

import marvin
from marvin.agents.actor import Actor
from marvin.engine.events import ToolResultEvent
from marvin.utilities.logging import get_logger

if TYPE_CHECKING:
    import marvin.agents.agent
    import marvin.engine.orchestrator

logger = get_logger(__name__)


class MCPManager:
    """Manager for MCP server lifecycle, separating concerns from the orchestrator."""

    def __init__(self):
        """Initialize the MCP manager."""
        self.exit_stack = AsyncExitStack()
        self.active_servers: list[MCPServer] = []

    async def start_servers(self, actor: "Actor") -> list[MCPServer]:
        """Start MCP servers for the given actor.

        Args:
            actor: The actor that potentially has MCP servers

        Returns:
            List of successfully started MCP servers
        """
        from marvin.agents.agent import Agent

        logger.debug(f"[MCPManager] Preparing MCP servers for {actor.name}...")
        self.active_servers = []

        if not isinstance(actor, Agent) or not hasattr(actor, "get_mcp_servers"):
            logger.debug(
                f"[MCPManager] Actor {actor.name} is not an Agent or does not have get_mcp_servers method."
            )
            return self.active_servers

        servers_to_manage = actor.get_mcp_servers()

        if not servers_to_manage:
            logger.debug(
                f"[MCPManager] Actor {actor.name} has no configured MCP servers."
            )
            return self.active_servers

        logger.debug(
            f"[MCPManager] Found {len(servers_to_manage)} server configurations."
        )

        for i, server in enumerate(servers_to_manage):
            logger.debug(
                f"[MCPManager] Processing server #{i + 1}: {type(server).__name__}"
            )
            try:
                # Set environment variables for stdio servers if not already set
                if isinstance(server, MCPServerStdio) and server.env is None:
                    logger.debug(
                        f"[MCPManager] Server #{i + 1} is MCPServerStdio with no env set. Setting env=dict(os.environ)."
                    )
                    server.env = dict(os.environ)

                logger.debug(f"[MCPManager] Entering context for server #{i + 1}...")
                await self.exit_stack.enter_async_context(server)
                self.active_servers.append(server)
                logger.debug(
                    f"[MCPManager] Context entered successfully for server #{i + 1}."
                )
            except Exception as e:
                logger.error(
                    f"[MCPManager] Failed to start MCP server #{i + 1} ({type(server).__name__}): {e}",
                    exc_info=True,
                )

        logger.debug(f"[MCPManager] Started {len(self.active_servers)} active servers.")
        return self.active_servers

    async def cleanup(self):
        """Clean up all started MCP servers."""
        logger.debug("[MCPManager] Cleaning up MCP servers...")
        await self.exit_stack.aclose()
        self.active_servers = []
        logger.debug("[MCPManager] MCP server cleanup complete.")


async def _mcp_tool_wrapper(
    *,
    _mcp_server: MCPServer,
    _tool_def: ToolDefinition,
    _orchestrator: "marvin.engine.orchestrator.Orchestrator | None",
    **kwargs: Any,
) -> Any:
    if not _orchestrator:
        raise RuntimeError("orchestrator not found, this is unexpected")

    tool_call_id = f"mcp-{uuid.uuid4()}"
    tool_name = _tool_def.name

    logger.debug(f"Calling MCP tool '{tool_name}' via {type(_mcp_server).__name__}")
    try:
        raw_mcp_output: Any = await _mcp_server.call_tool(
            tool_name=tool_name, arguments=kwargs
        )

        event_content: str | list[Any]

        if isinstance(raw_mcp_output, CallToolResult):
            texts = []
            if raw_mcp_output.content and isinstance(raw_mcp_output.content, list):
                for part in raw_mcp_output.content:
                    if (
                        hasattr(part, "type")
                        and part.type == "text"
                        and hasattr(part, "text")
                        and isinstance(part.text, str)
                    ):
                        texts.append(part.text)

            if len(texts) == 1:
                event_content = texts[0]
            elif len(texts) > 1:
                event_content = texts
            else:
                event_content = str(raw_mcp_output)
        elif isinstance(raw_mcp_output, (str, list)):
            event_content = raw_mcp_output
        elif (
            isinstance(raw_mcp_output, dict)
            and "type" in raw_mcp_output
            and "result" in raw_mcp_output
        ):
            # Handle the case where an MCP tool returns a structured response with "type" and "result" fields
            event_content = raw_mcp_output["result"]
            logger.debug(
                f"Extracted 'result' from structured response: {event_content!r}"
            )
        elif isinstance(raw_mcp_output, dict):
            event_content = str(raw_mcp_output)
        else:
            event_content = str(raw_mcp_output)

        await _orchestrator.handle_event(
            ToolResultEvent(
                message=ToolReturnPart(
                    tool_name=tool_name,
                    content=event_content,  # Use the adapted content
                    tool_call_id=tool_call_id,
                ),
            )
        )

        logger.debug(f"MCP tool '{tool_name}' returned result: {event_content!r}")
        return event_content
    except Exception as e:
        error_message = f"Error calling MCP tool '{tool_name}': {e}"
        logger.error(error_message, exc_info=True)
        try:
            await _orchestrator.handle_event(
                ToolResultEvent(
                    message=ToolReturnPart(
                        tool_name=tool_name,
                        content=error_message,
                        tool_call_id=tool_call_id,
                    )
                )
            )
        except Exception as e_inner:
            logger.error(
                f"Failed to create/send error ToolResultEvent for {tool_name}: {e_inner}",
                exc_info=True,
            )

        return error_message


async def discover_mcp_tools(
    mcp_servers: list[MCPServer],
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
                f"MCP Server {type(server).__name__} is not marked as running, skipping tool discovery."
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
                f"Failed to list tools from {type(server).__name__}: {result}",
                exc_info=result,
            )
            continue

        tool_defs: list[ToolDefinition] = result
        logger.debug(
            f"Discovered {len(tool_defs)} tool{'' if len(tool_defs) == 1 else 's'} from {type(server).__name__}"
        )
        for tool_def in tool_defs:
            wrapped_func = partial(
                _mcp_tool_wrapper,
                _mcp_server=server,
                _tool_def=tool_def,
                _orchestrator=orchestrator,
            )

            # Use a default argument to capture the current value of wrapped_func
            # This prevents the closure from capturing the loop variable by reference.
            async def async_wrapped_func_fixed(
                _bound_partial=wrapped_func,  # TODO: investigate type hinting here # pyright: ignore
                **kwargs: Any,
            ) -> Any:
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


@asynccontextmanager
async def manage_mcp_servers(actor: "Actor") -> AsyncIterator[list[MCPServer]]:
    """Context manager to start and stop MCP servers for a given actor.

    Args:
        actor: The actor that may have MCP servers

    Yields:
        List of successfully started MCP servers
    """
    # Early check for MCP servers to be more "lazy"
    from marvin.agents.agent import Agent

    has_mcp_servers = (
        isinstance(actor, Agent)
        and hasattr(actor, "get_mcp_servers")
        and actor.get_mcp_servers()
    )

    if not has_mcp_servers:
        # Empty list, no setup needed
        yield []
        return

    # Only create and use the manager if we actually have MCP servers
    manager = MCPManager()
    active_servers = await manager.start_servers(actor)

    try:
        yield active_servers
    finally:
        await manager.cleanup()
