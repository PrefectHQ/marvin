from typing import Any, Type

from mcp.types import CallToolResult
from mcp.types import Tool as MCPToolType
from pydantic_ai.mcp import MCPServer
from pydantic_ai.tools import ToolDefinition

from marvin.utilities.logging import get_logger

logger = get_logger(__name__)

_LazyFastMCPServerType: Type | None = None
_lazy_fastmcp_converter_func: Any | None = None
_fastmcp_import_attempted_flag: bool = False


class _FastMCPAdapter(MCPServer):
    def __init__(self, fastmcp_instance: Any):
        global _LazyFastMCPServerType
        if not _LazyFastMCPServerType or not isinstance(
            fastmcp_instance, _LazyFastMCPServerType
        ):
            raise TypeError(
                f"_FastMCPAdapter initialized with unexpected type: {type(fastmcp_instance)}"
            )
        self._fmcp: Any = fastmcp_instance
        self._is_running_flag = False

    async def __aenter__(self) -> "_FastMCPAdapter":
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
        raw_result_content = await self._fmcp._mcp_call_tool(tool_name, arguments)
        return CallToolResult(content=raw_result_content)

    @property
    def name(self) -> str:
        return self._fmcp.name

    def client_streams(self) -> list[Any]:
        return []

    def _get_log_level(self) -> str:
        return str(
            self._fmcp.settings.log_level
            if self._fmcp.settings
            and hasattr(self._fmcp.settings, "log_level")
            and self._fmcp.settings.log_level
            else "INFO"
        ).lower()


def _internal_pydantic_ai_mcp_server_from_fastmcp_server(server: Any) -> MCPServer:
    """Converts a FastMCPServer instance to an _FastMCPAdapter instance."""
    return _FastMCPAdapter(server)


def attempt_convert_to_pydantic_ai_mcp_server(obj: Any) -> MCPServer | None:
    """
    Attempts to convert an object to a pydantic_ai.mcp.MCPServer.
    If the object is already an MCPServer, it's returned directly.
    If it appears to be a FastMCP server, and marvin[mcp] is installed,
    it's converted. Otherwise, None is returned.
    """
    global \
        _LazyFastMCPServerType, \
        _lazy_fastmcp_converter_func, \
        _fastmcp_import_attempted_flag

    if isinstance(obj, MCPServer):
        return obj

    if not _fastmcp_import_attempted_flag:
        _fastmcp_import_attempted_flag = True
        try:
            from fastmcp.server import FastMCP as FastMCPServer_local

            _LazyFastMCPServerType = FastMCPServer_local
            _lazy_fastmcp_converter_func = (
                _internal_pydantic_ai_mcp_server_from_fastmcp_server
            )
            logger.debug(
                "Successfully imported FastMCP components for optional Marvin integration."
            )
        except ImportError:
            logger.debug(
                "marvin[mcp] extra not installed or fastmcp not found. "
                "FastMCP server instances will not be automatically converted."
            )

    if (
        _LazyFastMCPServerType is not None
        and _lazy_fastmcp_converter_func is not None
        and isinstance(obj, _LazyFastMCPServerType)
    ):
        return _lazy_fastmcp_converter_func(obj)

    return None
