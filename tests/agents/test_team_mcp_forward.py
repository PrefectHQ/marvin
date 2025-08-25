from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai.mcp import MCPServer

from marvin.agents.agent import Agent
from marvin.agents.team import Team


class DummyAgent(Agent):
from typing import Callable, Any

from marvin.agents.agent import Agent
from marvin.agents.team import Team


class DummyAgent(Agent):
    async def get_agentlet(
        self,
        tools: list[Callable[..., Any]],
        end_turn_tools: list["EndTurn"],
        active_mcp_servers: list[MCPServer] | None = None,
    ):
        # Assert that the forwarded arg is passed through
        self._seen_active_mcp_servers = active_mcp_servers
        # Return a minimal stub that satisfies Orchestrator usage patterns if needed
        stub = MagicMock()
        stub.iter = AsyncMock()
        return stub


@pytest.mark.asyncio
async def test_team_forwards_active_mcp_servers():
    mock_server = MagicMock(spec=MCPServer)

    a1 = DummyAgent(name="A1")
    a2 = DummyAgent(name="A2")
    team = Team(members=[a1, a2])

    await team.get_agentlet(tools=[], end_turn_tools=[], active_mcp_servers=[mock_server])

    assert getattr(team.active_member, "_seen_active_mcp_servers", None) == [mock_server]


