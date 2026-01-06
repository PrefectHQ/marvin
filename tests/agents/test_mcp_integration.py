from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai.mcp import MCPServer
from pydantic_ai.tools import ToolDefinition

from marvin._internal.integrations.mcp import (
    MCPManager,
    cleanup_thread_mcp_servers,
    discover_mcp_tools,
    get_thread_mcp_manager,
    manage_mcp_servers,
    set_thread_mcp_manager,
)
from marvin.agents import Agent
from marvin.thread import Thread


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


async def test_mcp_tools_not_duplicated():
    """
    regression for https://github.com/prefecthq/marvin/issues/1142: MCP tools appear to be added twice.

    The issue: Marvin pre-discovered MCP tools AND passed mcp_servers to pydantic-ai.
    In pydantic-ai's _prepare_request_parameters(), both were processed:
    - add_tool(ctx.deps.function_tools.values()) - Marvin's pre-discovered tools
    - add_mcp_server_tools(ctx.deps.mcp_servers) - pydantic-ai's native discovery
    This caused duplicate tool names sent to the LLM.

    The fix: Remove Marvin's pre-discovery, let pydantic-ai handle MCP servers natively.
    """
    from pydantic_ai.mcp import MCPServerStdio

    git_mcp_server = MCPServerStdio(command="uvx", args=["mcp-server-git"])
    agent = Agent(mcp_servers=[git_mcp_server])

    agent_tools = agent.get_tools()
    tool_names = [getattr(tool, "__name__", str(tool)) for tool in agent_tools]

    mcp_tool_names = ["git_log", "git_status", "git_diff"]
    found_mcp_tools = [
        name for name in tool_names if any(mcp in name for mcp in mcp_tool_names)
    ]

    assert len(found_mcp_tools) == 0, (
        f"Agent should not pre-discover MCP tools, found: {found_mcp_tools}"
    )


class TestMCPServerLifecycleInThreadContext:
    """
    Regression tests for https://github.com/prefecthq/marvin/issues/1259:
    MCP servers restart for each agent.run() call instead of staying alive for session.
    """

    async def test_mcp_servers_reused_within_thread_context(self):
        """MCP servers should be started once and reused across multiple manage_mcp_servers calls."""
        # Setup: Create a mock server
        mock_server = MagicMock(spec=MCPServer)
        mock_server.is_running = True

        # Create an agent with the mock server
        mock_agent = MagicMock(spec=Agent)
        mock_agent.name = "TestAgent"
        mock_agent.get_mcp_servers.return_value = [mock_server]

        # Clear any existing thread MCP manager
        set_thread_mcp_manager(None)

        try:
            # Patch MCPManager.start_servers to track calls without actually starting servers
            start_call_count = 0

            async def mock_start_servers(self, actor):
                nonlocal start_call_count
                start_call_count += 1
                # Track that we "started" this server
                server_id = id(mock_server)
                if server_id not in self._started_server_ids:
                    self._started_server_ids.add(server_id)
                    self.active_servers.append(mock_server)
                return self.active_servers

            with patch.object(MCPManager, "start_servers", mock_start_servers):
                # First call to manage_mcp_servers should create a new manager
                async with manage_mcp_servers(mock_agent) as servers1:
                    assert len(servers1) == 1
                    manager1 = get_thread_mcp_manager()
                    assert manager1 is not None

                    # Second call within same thread context should reuse the manager
                    async with manage_mcp_servers(mock_agent) as servers2:
                        assert len(servers2) == 1
                        manager2 = get_thread_mcp_manager()
                        # Same manager instance should be reused
                        assert manager1 is manager2
                        # Server should be reused (start only called once per new server)
                        assert (
                            start_call_count == 2
                        )  # Called twice, but server only added once

                    # Third call should still reuse
                    async with manage_mcp_servers(mock_agent) as servers3:
                        assert len(servers3) == 1
                        manager3 = get_thread_mcp_manager()
                        assert manager1 is manager3
        finally:
            # Cleanup
            await cleanup_thread_mcp_servers()

    async def test_mcp_manager_tracks_started_servers_by_id(self):
        """MCPManager should track servers by id to avoid restarting the same server."""
        manager = MCPManager()

        mock_server = MagicMock(spec=MCPServer)
        server_id = id(mock_server)

        # Simulate starting the server
        manager._started_server_ids.add(server_id)
        manager.active_servers.append(mock_server)

        # The server should be considered already started
        assert server_id in manager._started_server_ids
        assert mock_server in manager.active_servers

        # Cleanup should clear the tracking
        manager.active_servers = []
        manager._started_server_ids.clear()
        assert server_id not in manager._started_server_ids

    async def test_mcp_cleanup_happens_in_orchestrator_not_thread(self):
        """MCP cleanup should happen in orchestrator's finally block, not Thread.__exit__.

        This is important because Thread.__exit__ is sync but MCP cleanup is async.
        The orchestrator handles cleanup after the Thread context exits.
        """
        # Setup: Create a mock MCP manager with a server
        mock_server = MagicMock(spec=MCPServer)
        mock_server.is_running = True

        manager = MCPManager()
        manager.active_servers = [mock_server]
        manager._started_server_ids.add(id(mock_server))

        # Mock the cleanup method
        manager.cleanup = AsyncMock()

        # Set as the thread's MCP manager
        set_thread_mcp_manager(manager)

        # Create a thread and enter/exit its context
        thread = Thread()
        with thread:
            # Manager should still be set inside the context
            assert get_thread_mcp_manager() is manager

        # After Thread exits, cleanup should NOT have been called yet
        # (cleanup now happens in orchestrator.run(), not Thread.__exit__)
        manager.cleanup.assert_not_called()

        # Manager should still be set (orchestrator would clean it up)
        assert get_thread_mcp_manager() is manager

        # Manual cleanup to simulate what orchestrator does
        await cleanup_thread_mcp_servers()
        manager.cleanup.assert_called_once()

        # Clean up test state
        set_thread_mcp_manager(None)

    async def test_manage_mcp_servers_no_servers_no_manager_created(self):
        """When an agent has no MCP servers, no manager should be created."""
        mock_agent = MagicMock(spec=Agent)
        mock_agent.name = "NoMCPAgent"
        mock_agent.get_mcp_servers.return_value = []

        # Clear any existing manager
        set_thread_mcp_manager(None)

        async with manage_mcp_servers(mock_agent) as servers:
            assert servers == []
            # No manager should be created for empty servers
            assert get_thread_mcp_manager() is None

    async def test_mcp_manager_contextvar_isolation(self):
        """MCPManager ContextVar should be isolated between different async contexts."""
        # This test verifies that the ContextVar behaves correctly
        manager1 = MCPManager()
        manager2 = MCPManager()

        # Initially no manager
        set_thread_mcp_manager(None)
        assert get_thread_mcp_manager() is None

        # Set manager1
        set_thread_mcp_manager(manager1)
        assert get_thread_mcp_manager() is manager1

        # Set manager2 (overwrites manager1 in this context)
        set_thread_mcp_manager(manager2)
        assert get_thread_mcp_manager() is manager2

        # Cleanup
        set_thread_mcp_manager(None)
        assert get_thread_mcp_manager() is None

    async def test_cleanup_from_async_context_works(self):
        """MCP cleanup should work correctly when called from async context.

        This is a regression test for the issue where calling run_sync() from
        Thread.__exit__ while already in an async context caused problems.
        The fix moves cleanup to orchestrator.run() which is already async.
        """
        mock_server = MagicMock(spec=MCPServer)
        mock_server.is_running = True

        manager = MCPManager()
        manager.active_servers = [mock_server]
        manager._started_server_ids.add(id(mock_server))
        manager.cleanup = AsyncMock()

        set_thread_mcp_manager(manager)

        # Simulate what orchestrator.run() does: enter Thread, do work, exit Thread, then cleanup
        thread = Thread()
        with thread:
            # Work happens here
            pass

        # After Thread.__exit__, we're still in async context
        # Cleanup should work without issues (no run_sync needed)
        await cleanup_thread_mcp_servers()

        # Verify cleanup was called
        manager.cleanup.assert_called_once()
        assert get_thread_mcp_manager() is None
