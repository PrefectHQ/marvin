"""
Experimental module for integrating Model Context Protocol (MCP) servers with Marvin.
"""

import asyncio
import os
import uuid
from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar
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
    import marvin.engine.orchestrator

logger = get_logger(__name__)

# Context variable to store the active MCP manager for the current thread context.
# This allows MCP servers to persist across multiple orchestrator runs within
# the same marvin.Thread() context.
_thread_mcp_manager: ContextVar["MCPManager | None"] = ContextVar(
    "thread_mcp_manager",
    default=None,
)


def _get_server_name(server: MCPServer) -> str:
    return getattr(server, "name", type(server).__name__)


class MCPManager:
    """Manager for MCP server lifecycle, separating concerns from the orchestrator.

    The manager tracks servers by their object id, allowing the same server instance
    to be reused across multiple orchestrator runs. This is important because
    pydantic-ai's MCPServer uses reference counting - if we enter the same server's
    context multiple times, it just increments the count and only stops when it hits 0.
    """

    def __init__(self):
        """Initialize the MCP manager."""
        self.exit_stack = AsyncExitStack()
        self.active_servers: list[MCPServer] = []
        # Track which server instances (by id) have been started
        self._started_server_ids: set[int] = set()

    async def start_servers(self, actor: "Actor") -> list[MCPServer]:
        """Start MCP servers for the given actor.

        If a server is already running (from a previous orchestrator run in the same
        thread context), it will be reused rather than started again.

        Args:
            actor: The actor that potentially has MCP servers

        Returns:
            List of successfully started MCP servers
        """
        from marvin.agents.agent import Agent

        logger.debug(f"[MCPManager] Preparing MCP servers for {actor.name}...")

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
            server_id = id(server)
            server_repr = f"#{i + 1} {_get_server_name(server)}"

            # Check if this server instance is already started
            if server_id in self._started_server_ids:
                logger.debug(
                    f"[MCPManager] Server {server_repr} is already running, reusing."
                )
                if server not in self.active_servers:
                    self.active_servers.append(server)
                continue

            try:
                # Set environment variables for stdio servers if not already set
                if isinstance(server, MCPServerStdio) and server.env is None:
                    logger.debug(
                        f"[MCPManager] Server {server_repr} has no env set. Setting env=dict(os.environ)."
                    )
                    server.env = dict(os.environ)

                await self.exit_stack.enter_async_context(server)
                self.active_servers.append(server)
                self._started_server_ids.add(server_id)
                logger.debug(
                    f"[MCPManager] Context successfully entered for server {server_repr}."
                )
            except Exception as e:
                logger.error(
                    f"[MCPManager] Failed to start/enter context for MCP server {server_repr}: {e}",
                    exc_info=True,
                )

        logger.debug(
            f"[MCPManager] {len(self.active_servers)} active servers available."
        )
        return self.active_servers

    async def cleanup(self):
        """Clean up all started MCP servers."""
        logger.debug("[MCPManager] Cleaning up MCP servers...")
        await self.exit_stack.aclose()
        self.active_servers = []
        self._started_server_ids.clear()
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
    server_name = _get_server_name(_mcp_server)

    logger.debug(f"Calling MCP tool '{tool_name}' via server '{server_name}'")
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
                f"MCP Server '{_get_server_name(server)}' is not marked as running, skipping tool discovery."
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
                f"Failed to list tools from server '{_get_server_name(server)}': {result}",
                exc_info=result,
            )
            continue

        tool_defs: list[ToolDefinition] = result
        logger.debug(
            f"Discovered {len(tool_defs)} tool{'' if len(tool_defs) == 1 else 's'} from server '{_get_server_name(server)}'"
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


def get_thread_mcp_manager() -> "MCPManager | None":
    """Get the current thread's MCP manager from context."""
    return _thread_mcp_manager.get()


def set_thread_mcp_manager(manager: "MCPManager | None") -> None:
    """Set the MCP manager for the current thread context."""
    _thread_mcp_manager.set(manager)


async def cleanup_thread_mcp_servers() -> None:
    """Clean up MCP servers for the current thread context.

    This should be called when the Thread context exits to properly
    shut down any MCP servers that were started.
    """
    manager = get_thread_mcp_manager()
    if manager is not None:
        await manager.cleanup()
        set_thread_mcp_manager(None)


@asynccontextmanager
async def manage_mcp_servers(actor: "Actor") -> AsyncIterator[list[MCPServer]]:
    """Context manager to manage MCP servers for a given actor.

    MCP servers are persisted across multiple orchestrator runs within the same
    Thread context. This avoids the overhead of starting/stopping servers for
    each agent.run() call when multiple runs happen within the same Thread.

    The servers are only cleaned up when the Thread context exits (via
    cleanup_thread_mcp_servers()).

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

    # Get or create the manager for this thread context
    manager = get_thread_mcp_manager()
    if manager is None:
        manager = MCPManager()
        set_thread_mcp_manager(manager)
        logger.debug("[manage_mcp_servers] Created new MCPManager for thread context")
    else:
        logger.debug(
            "[manage_mcp_servers] Reusing existing MCPManager from thread context"
        )

    # Start servers (MCPManager will skip already-running servers)
    active_servers = await manager.start_servers(actor)

    # Yield the servers - don't clean up on exit, let the Thread handle it
    yield active_servers
