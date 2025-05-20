from typing import Any, Callable

from mcp.types import CallToolResult
from mcp.types import Tool as MCPToolType
from pydantic_ai.mcp import MCPServer
from pydantic_ai.tools import ToolDefinition

from marvin.utilities.logging import get_logger

logger = get_logger(__name__)


class _FastMCPImportState:
    """Manages the import state for FastMCP integration."""

    def __init__(self):
        self.server_type: type | None = None
        self.converter_func: Callable[[Any], MCPServer] | None = None
        self.import_attempted: bool = False

    def attempt_import(self) -> None:
        """Attempt to import FastMCP components."""
        if self.import_attempted:
            return

        self.import_attempted = True
        try:
            from fastmcp.server import FastMCP as FastMCPServer_local  # type: ignore

            self.server_type = FastMCPServer_local
            self.converter_func = lambda server: _FastMCPAdapter(server)

            logger.debug(
                "Successfully imported FastMCP components for optional Marvin integration."
            )
        except ImportError:
            logger.debug(
                "marvin[mcp] extra not installed or fastmcp not found. "
                "FastMCP server instances will not be automatically converted."
            )


_import_state = _FastMCPImportState()


class _FastMCPAdapter(MCPServer):
    def __init__(self, fastmcp_instance: Any):
        obj_type = type(fastmcp_instance)
        obj_type_name = obj_type.__name__
        obj_type_module = getattr(obj_type, "__module__", "unknown")

        if not hasattr(fastmcp_instance, "name"):
            raise TypeError(f"FastMCP object missing 'name' attribute: {obj_type_name}")

        self._direct_list_tools = hasattr(fastmcp_instance, "list_tools")
        self._direct_call_tool = hasattr(fastmcp_instance, "call_tool")

        self._mcp_list_tools = hasattr(fastmcp_instance, "_mcp_list_tools")
        self._mcp_call_tool = hasattr(fastmcp_instance, "_mcp_call_tool")

        if not (self._direct_list_tools or self._mcp_list_tools):
            raise TypeError(
                "FastMCP object missing both 'list_tools' and '_mcp_list_tools' methods"
            )

        if not (self._direct_call_tool or self._mcp_call_tool):
            raise TypeError(
                "FastMCP object missing both 'call_tool' and '_mcp_call_tool' methods"
            )

        logger.debug(
            f"Adapting FastMCP-compatible object: {obj_type_name} from {obj_type_module}"
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
        if self._mcp_list_tools:
            # Use the internal MCP method if available
            mcp_tools_list: list[MCPToolType] = await self._fmcp._mcp_list_tools()
        elif self._direct_list_tools:
            # Use the direct method otherwise
            mcp_tools_list: list[MCPToolType] = await self._fmcp.list_tools()
        else:
            # This shouldn't happen due to our checks in __init__
            raise RuntimeError("No method available to list tools")

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

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> CallToolResult:
        if self._mcp_call_tool:
            # Use the internal MCP method if available
            raw_result_content = await self._fmcp._mcp_call_tool(tool_name, arguments)
        elif self._direct_call_tool:
            # Use the direct method otherwise
            raw_result_content = await self._fmcp.call_tool(tool_name, arguments)
        else:
            raise RuntimeError("No method available to call tools")

        return CallToolResult(content=raw_result_content)

    @property
    def name(self) -> str:
        return self._fmcp.name

    def client_streams(self) -> list[Any]:
        return []

    def _get_log_level(self) -> str:
        return str(
            self._fmcp.settings.log_level
            if hasattr(self._fmcp, "settings")
            and self._fmcp.settings
            and hasattr(self._fmcp.settings, "log_level")
            and self._fmcp.settings.log_level
            else "INFO"
        ).lower()


def attempt_convert_to_pydantic_ai_mcp_server(obj: Any) -> MCPServer | None:
    """
    Attempts to convert an object to a pydantic_ai.mcp.MCPServer.
    If the object is already an MCPServer, it's returned directly.
    If it appears to be a FastMCP server, and marvin[mcp] is installed,
    it's converted. Otherwise, None is returned.
    """
    if isinstance(obj, MCPServer):
        return obj

    _import_state.attempt_import()

    obj_type = type(obj)
    obj_type_name = obj_type.__name__

    looks_like_fastmcp = False

    # Check by class name
    if "FastMCP" in obj_type_name:
        looks_like_fastmcp = True

    # Check by method presence
    has_fastmcp_methods = (
        hasattr(obj, "name")
        and (hasattr(obj, "list_tools") or hasattr(obj, "_mcp_list_tools"))
        and (hasattr(obj, "call_tool") or hasattr(obj, "_mcp_call_tool"))
    )

    if has_fastmcp_methods:
        looks_like_fastmcp = True

    if looks_like_fastmcp:
        # First check if it's the exact type we imported
        if _import_state.server_type is not None and isinstance(
            obj, _import_state.server_type
        ):
            logger.debug("Object is an instance of the imported FastMCP type")
            assert _import_state.converter_func is not None
            return _import_state.converter_func(obj)

        # If not the exact type but has the right interface, try to adapt it anyway
        if _import_state.converter_func is not None:
            try:
                logger.debug(
                    "Object looks like a FastMCP-compatible type, attempting to adapt"
                )
                return _import_state.converter_func(obj)
            except Exception as e:
                logger.error(f"Failed to adapt FastMCP-like object: {e}")
                raise
        else:
            # If the conversion function isn't available, FastMCP isn't installed
            raise ImportError(
                "Cannot use FastMCP server: marvin[mcp] extra is not installed. "
                "Please install `marvin[mcp]` to use FastMCP servers with Marvin."
            )

    return None
