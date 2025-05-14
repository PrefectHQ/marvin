from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.mcp import MCPServer
from pydantic_ai.tools import ToolDefinition

from marvin._internal.integrations.mcp import discover_mcp_tools
from marvin.agents import Agent


class TestAgentMCPInstantiation:
    def test_agent_instantiation_with_mcp_servers(self):
        mock_server_1 = MagicMock(spec=MCPServer)
        mock_server_2 = MagicMock(spec=MCPServer)

        agent = Agent(name="TestMCPAgent", mcp_servers=[mock_server_1, mock_server_2])

        assert agent.name == "TestMCPAgent"
        assert agent.get_mcp_servers() == [mock_server_1, mock_server_2]
        assert agent.mcp_servers == [mock_server_1, mock_server_2]

    def test_get_mcp_servers_empty_list(self):
        """Test get_mcp_servers returns an empty list if none are provided."""
        agent = Agent(name="NoMCPAgent")
        assert agent.get_mcp_servers() == []

    def test_get_mcp_servers_default_is_empty(self):
        """Test the default value for mcp_servers is an empty list."""
        agent = Agent(name="DefaultMCPAgent")
        assert agent.mcp_servers == []
        assert agent.get_mcp_servers() == []


# More tests will be needed later to verify interaction with Orchestrator
# and potentially mocking the server communication (list_tools, call_tool).


async def test_discover_mcp_tools_success():
    """Test discovering tools from mock MCP servers."""
    mock_orchestrator = MagicMock()

    # Mock Tool Definitions
    mock_tool_def_1 = ToolDefinition(
        name="tool_one",
        description="Description for tool one",
        parameters_json_schema={
            "type": "object",
            "properties": {"arg1": {"type": "string"}},
        },
    )
    mock_tool_def_2 = ToolDefinition(
        name="tool_two",
        description="Description for tool two",
        parameters_json_schema={
            "type": "object",
            "properties": {"argX": {"type": "integer"}},
        },
    )

    # Mock MCP Servers
    mock_server_1 = MagicMock(spec=MCPServer)
    mock_server_1.list_tools = AsyncMock(return_value=[mock_tool_def_1])
    mock_server_1.is_running = True  # Assume it's running

    mock_server_2 = MagicMock(spec=MCPServer)
    mock_server_2.list_tools = AsyncMock(return_value=[mock_tool_def_2])
    mock_server_2.is_running = True

    # Call the discovery function
    discovered_tools = await discover_mcp_tools(
        mcp_servers=[mock_server_1, mock_server_2],
        orchestrator=mock_orchestrator,
    )

    # Assertions
    assert len(discovered_tools) == 2
    assert discovered_tools[0].name == "tool_one"
    assert discovered_tools[0].description == "Description for tool one"
    assert discovered_tools[1].name == "tool_two"
    assert discovered_tools[1].description == "Description for tool two"
    # We could potentially inspect the wrapped function or parameters_schema if needed


async def test_discover_mcp_tools_server_not_running():
    """Test that tools are not discovered if server.is_running is False."""
    mock_orchestrator = MagicMock()
    mock_tool_def_1 = ToolDefinition(
        name="tool_one", description="Desc", parameters_json_schema={}
    )

    mock_server_1 = MagicMock(spec=MCPServer)
    mock_server_1.list_tools = AsyncMock(return_value=[mock_tool_def_1])
    mock_server_1.is_running = False  # Explicitly set to False

    discovered_tools = await discover_mcp_tools(
        mcp_servers=[mock_server_1],
        orchestrator=mock_orchestrator,
    )

    assert len(discovered_tools) == 0  # No tools should be discovered


async def test_discover_mcp_tools_discovery_error():
    """Test that discovery proceeds if one server fails to list tools."""
    mock_orchestrator = MagicMock()
    mock_tool_def_2 = ToolDefinition(
        name="tool_two", description="Desc 2", parameters_json_schema={}
    )

    # Server 1 raises an exception during list_tools
    mock_server_1 = MagicMock(spec=MCPServer)
    mock_server_1.list_tools = AsyncMock(side_effect=RuntimeError("Discovery failed!"))
    mock_server_1.is_running = True

    # Server 2 works fine
    mock_server_2 = MagicMock(spec=MCPServer)
    mock_server_2.list_tools = AsyncMock(return_value=[mock_tool_def_2])
    mock_server_2.is_running = True

    discovered_tools = await discover_mcp_tools(
        mcp_servers=[mock_server_1, mock_server_2],
        orchestrator=mock_orchestrator,
    )

    # Only tool from server 2 should be discovered
    assert len(discovered_tools) == 1
    assert discovered_tools[0].name == "tool_two"


async def test_manage_mcp_servers_lazy_behavior():
    """Test that manage_mcp_servers is lazy and doesn't set up anything when no MCP servers exist."""

    from marvin._internal.integrations.mcp import MCPManager, manage_mcp_servers

    # Setup: Mock Agent with no MCP servers
    mock_agent = MagicMock(spec=Agent)
    mock_agent.get_mcp_servers.return_value = []

    # Execute: Use the context manager
    async with manage_mcp_servers(mock_agent) as active_servers:
        # Assert: No servers should be returned
        assert active_servers == []

    # Setup: Mock Agent that is not an Agent type
    non_agent = MagicMock()

    # Execute: Use the context manager
    async with manage_mcp_servers(non_agent) as active_servers:
        # Assert: No servers should be returned
        assert active_servers == []

    # Setup: Mock Agent with MCP servers
    mock_agent_with_servers = MagicMock(spec=Agent)
    mock_server = MagicMock(spec=MCPServer)
    mock_agent_with_servers.get_mcp_servers.return_value = [mock_server]

    # We'll need to patch the MCPManager to avoid actual MCP server interaction
    original_start_servers = MCPManager.start_servers
    try:
        # Replace the start_servers method with a mock
        MCPManager.start_servers = AsyncMock(return_value=[mock_server])

        # Execute: Use the context manager
        async with manage_mcp_servers(mock_agent_with_servers) as active_servers:
            # Assert: Our mock server should be returned
            assert active_servers == [mock_server]
    finally:
        # Restore the original method
        MCPManager.start_servers = original_start_servers
