import asyncio
import json

import httpx

from slack_search import client


async def test_turso_requests_can_progress_concurrently(monkeypatch):
    both_started = asyncio.Event()
    requests = []

    async def respond(request):
        requests.append(json.loads(request.content))
        if len(requests) == 2:
            both_started.set()
        # Neither response can finish until the other request makes progress.
        await asyncio.wait_for(both_started.wait(), timeout=2)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "type": "ok",
                        "response": {
                            "result": {
                                "cols": [{"name": "text"}],
                                "rows": [[{"type": "text", "value": "found"}]],
                            }
                        },
                    }
                ]
            },
        )

    async_client = httpx.AsyncClient
    monkeypatch.setattr(
        client.httpx,
        "AsyncClient",
        lambda: async_client(transport=httpx.MockTransport(respond)),
    )
    monkeypatch.setattr(
        client,
        "get_settings",
        lambda: client.Settings(
            turso_url="libsql://test.invalid", turso_token="test-token", _env_file=None
        ),
    )

    def reject_sync(*args, **kwargs):
        raise AssertionError("Synchronous HTTP would block the MCP event loop")

    monkeypatch.setattr(client.httpx, "post", reject_sync)
    results = await asyncio.gather(
        client.turso_query("SELECT ?", ["first"]),
        client.turso_query("SELECT ?", ["second"]),
    )
    assert results == [[{"text": "found"}], [{"text": "found"}]]
    assert {request["requests"][0]["stmt"]["args"][0]["value"] for request in requests} == {
        "first",
        "second",
    }
