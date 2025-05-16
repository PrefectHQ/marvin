from typing import Any, Self

from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport
from mcp.types import GetPromptResult, Prompt, Resource, Tool
from pydantic_ai.mcp import MCPServerHTTP


class MCPServerStreamHTTP(MCPServerHTTP):
    def __init__(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ):
        self._fastmcp_client = Client(
            transport=StreamableHttpTransport(url=url, headers=headers)
        )

    # ––––– context-manager life-cycle –––––
    async def __aenter__(self) -> Self:
        await self._fastmcp_client.__aenter__()
        self.is_running = True
        return self

    async def __aexit__(self, *exc):
        await self._fastmcp_client.__aexit__(*exc)  # close the HTTP session
        self.is_running = False

    # ––––– thin pass-throughs –––––
    async def list_tools(self) -> list[Tool]:
        return await self._fastmcp_client.list_tools()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        return await self._fastmcp_client.call_tool(tool_name, arguments)

    async def list_resources(self) -> list[Resource]:
        return await self._fastmcp_client.list_resources()

    async def read_resource(self, uri: str) -> list[Any]:
        return await self._fastmcp_client.read_resource(uri)

    async def list_prompts(self) -> list[Prompt]:
        return await self._fastmcp_client.list_prompts()

    async def get_prompt(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> GetPromptResult:
        return await self._fastmcp_client.get_prompt(name, arguments)
