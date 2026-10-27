import pytest

from marvin import Agent
from marvin._internal.integrations.mcp import MCPManager
from marvin._internal.pydantic_ai import MCPServerStdio


@pytest.mark.skipif(
    MCPServerStdio is not None, reason="requires current MCPToolset API"
)
async def test_fastmcp_tool_calls_and_cleanup():
    from fastmcp import FastMCP
    from fastmcp.exceptions import ToolError

    server = FastMCP("compatibility")

    @server.tool
    async def divide(a: int, b: int) -> float:
        return a / b

    agent = Agent(mcp_servers=[server])
    toolset = agent.get_mcp_servers()[0]
    manager = MCPManager()
    try:
        assert await manager.start_servers(agent) == [toolset]
        result = await toolset.client.call_tool("divide", {"a": 84, "b": 2})
        assert result.data == 42
        with pytest.raises(ToolError):
            await toolset.client.call_tool("divide", {"a": 84, "b": 0})
        assert await manager.start_servers(agent) == [toolset]
        assert len(manager.active_servers) == 1
        assert agent.get_mcp_servers()[0] is toolset
        result = await toolset.client.call_tool("divide", {"a": 30, "b": 2})
        assert result.data == 15
    finally:
        await manager.cleanup()
    assert not toolset.client.is_connected()
