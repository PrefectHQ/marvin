from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.mcp import MCPServer
from pydantic_ai.tools import ToolDefinition

from marvin._internal.integrations._mcp import discover_mcp_tools
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
    mock_actor = MagicMock(spec=Agent)
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
        actor=mock_actor,
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
    mock_actor = MagicMock(spec=Agent)
    mock_orchestrator = MagicMock()
    mock_tool_def_1 = ToolDefinition(
        name="tool_one", description="Desc", parameters_json_schema={}
    )

    mock_server_1 = MagicMock(spec=MCPServer)
    mock_server_1.list_tools = AsyncMock(return_value=[mock_tool_def_1])
    mock_server_1.is_running = False  # Explicitly set to False

    discovered_tools = await discover_mcp_tools(
        mcp_servers=[mock_server_1],
        actor=mock_actor,
        orchestrator=mock_orchestrator,
    )

    assert len(discovered_tools) == 0  # No tools should be discovered


async def test_discover_mcp_tools_discovery_error():
    """Test that discovery proceeds if one server fails to list tools."""
    mock_actor = MagicMock(spec=Agent)
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
        actor=mock_actor,
        orchestrator=mock_orchestrator,
    )

    # Only tool from server 2 should be discovered
    assert len(discovered_tools) == 1
    assert discovered_tools[0].name == "tool_two"
