from typing import Any

from pydantic_ai.mcp import MCPToolset


def attempt_convert_to_pydantic_ai_mcp_server(obj: Any) -> MCPToolset | None:
    """Return `obj` as an `MCPToolset`, or None if it is not an MCP server.

    An `MCPToolset` is returned unchanged. A `fastmcp.FastMCP` server is
    wrapped in an `MCPToolset` that connects to it in process. Any other
    object returns None.
    """
    if isinstance(obj, MCPToolset):
        return obj
    try:
        # The base install has only the fastmcp client. FastMCP servers need
        # the `marvin[mcp]` extra.
        from fastmcp import FastMCP
    except ImportError:
        return None
    if isinstance(obj, FastMCP):
        return MCPToolset(obj)
    return None
