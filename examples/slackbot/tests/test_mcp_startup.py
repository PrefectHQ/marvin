import asyncio
import json
from unittest.mock import Mock

import httpx
import pytest
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.test import TestModel
from slackbot import core
from slackbot._internal.tolerant_toolset import TolerantToolset


async def test_cold_start_exceeds_default_but_fits_bot_deadline(monkeypatch):
    async def endpoint(request):
        if request.method != "POST":
            return httpx.Response(405)
        body = json.loads(request.content)
        if body["method"] == "initialize":
            await asyncio.sleep(6)
            result = {
                "protocolVersion": "2025-11-25",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "cold-search", "version": "1"},
            }
        elif body["method"] == "tools/list":
            result = {"tools": []}
        else:
            return httpx.Response(202)
        return httpx.Response(
            200, json={"jsonrpc": "2.0", "id": body["id"], "result": result}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(endpoint)) as http:
        old = TolerantToolset(
            MCPServerStreamableHTTP("https://search.invalid/mcp", http_client=http)
        )
        async with old:
            assert not old._available

        servers = []

        def server_factory(**kwargs):
            server = MCPServerStreamableHTTP(**kwargs, http_client=http)
            servers.append(server)
            return server

        monkeypatch.setattr(core, "MCPServerStreamableHTTP", server_factory)
        monkeypatch.setattr(core, "get_run_logger", Mock())
        monkeypatch.setattr(core, "_base_system_prompt", lambda: "")
        core.create_agent(model=TestModel())
        fixed = TolerantToolset(servers[0])
        async with fixed:
            assert fixed._available
            assert await servers[0].list_tools() == []


@pytest.mark.parametrize("method", ["__aenter__", "get_tools", "__aexit__"])
async def test_external_cancellation_is_not_swallowed(method):
    from unittest.mock import AsyncMock

    inner = Mock()
    setattr(inner, method, AsyncMock(side_effect=asyncio.CancelledError))
    wrapper = TolerantToolset(inner)
    wrapper._available = True
    args = {"__aenter__": (), "get_tools": (None,), "__aexit__": (None, None, None)}[
        method
    ]
    with pytest.raises(asyncio.CancelledError):
        await getattr(wrapper, method)(*args)
