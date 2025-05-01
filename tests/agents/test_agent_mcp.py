from unittest.mock import MagicMock

from pydantic_ai.mcp import MCPServer

from marvin.agents import Agent


class TestAgentMCP:
    def test_agent_instantiation_with_mcp_servers(self):
        """Test that an Agent can be instantiated with MCPServer instances."""
        # Use MagicMock to simulate MCPServer objects without needing
        # the actual mcp library installed or complex setup.
        mock_server_1 = MagicMock(spec=MCPServer)
        mock_server_2 = MagicMock(spec=MCPServer)

        agent = Agent(name="TestMCPAgent", mcp_servers=[mock_server_1, mock_server_2])

        assert agent.name == "TestMCPAgent"
        assert agent.get_mcp_servers() == [mock_server_1, mock_server_2]

    def test_get_mcp_servers_empty_list(self):
        """Test get_mcp_servers returns an empty list if none are provided."""
        agent = Agent(name="NoMCPAgent")
        assert agent.get_mcp_servers() == []

    def test_get_mcp_servers_default_is_empty(self):
        """Test the default value for mcp_servers is an empty list."""
        agent = Agent(name="DefaultMCPAgent")
        # Access the field directly for default check if necessary,
        # although get_mcp_servers() should suffice.
        assert agent.mcp_servers == []
        assert agent.get_mcp_servers() == []


# More tests will be needed later to verify interaction with Orchestrator
# and potentially mocking the server communication (list_tools, call_tool).
