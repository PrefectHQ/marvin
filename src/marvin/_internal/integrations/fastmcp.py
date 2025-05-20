from typing import Any

from fastmcp.server import FastMCP as FastMCPServer
from mcp.types import CallToolResult
from mcp.types import Tool as MCPToolType
from pydantic_ai.mcp import MCPServer
from pydantic_ai.tools import ToolDefinition


class _FastMCPAdapter(MCPServer):
    def __init__(self, fastmcp_instance: FastMCPServer):
        self._fmcp = fastmcp_instance
        self._is_running_flag = False

    async def __aenter__(self) -> "_FastMCPAdapter":
        # The lifecycle of the actual FastMCP server is managed externally.
        # This adapter's lifecycle is primarily for Pydantic AI's MCPManager.
        self._is_running_flag = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        self._is_running_flag = False

    @property
    def is_running(self) -> bool:
        return self._is_running_flag

    async def list_tools(self) -> list[ToolDefinition]:
        mcp_tools_list: list[MCPToolType] = await self._fmcp._mcp_list_tools()
        pydantic_ai_tool_defs: list[ToolDefinition] = []
        for mcp_tool_item in mcp_tools_list:
            pydantic_ai_tool_defs.append(
                ToolDefinition(
                    name=mcp_tool_item.name,
                    description=mcp_tool_item.description or "",
                    parameters_json_schema=mcp_tool_item.inputSchema,
                )
            )
        return pydantic_ai_tool_defs

    async def call_tool(self, tool_name: str, arguments: dict) -> CallToolResult:
        # FastMCP's _mcp_call_tool is expected to return list[TextContent | ImageContent | EmbeddedResource]
        # Pydantic AI's call_tool is expected to return CallToolResult
        # CallToolResult has a 'content: Any' field.
        raw_result_content = await self._fmcp._mcp_call_tool(tool_name, arguments)
        return CallToolResult(content=raw_result_content)

    @property
    def name(self) -> str:
        return self._fmcp.name

    # --- Methods to satisfy MCPServer ABC ---
    def client_streams(self) -> list[Any]:
        """
        FastMCP does not expose client streams in the same way as MCPServerStdio.
        Return empty list as a sensible default for the adapter.
        """
        return []

    def _get_log_level(self) -> str:
        """
        Returns the log level from FastMCP settings.
        """
        return str(
            self._fmcp.settings.log_level
            if self._fmcp.settings
            and hasattr(self._fmcp.settings, "log_level")
            and self._fmcp.settings.log_level
            else "INFO"
        ).lower()


def _pydantic_ai_mcp_server_from_fastmcp_server(server: FastMCPServer) -> MCPServer:
    return _FastMCPAdapter(server)
