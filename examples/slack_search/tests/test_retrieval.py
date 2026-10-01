import json
import sqlite3
import time
from unittest.mock import patch

import pytest
from fastmcp import Client

from slack_search import client

with patch.object(client, "get_settings", return_value=client.Settings(_env_file=None)):
    from slack_search import server


@pytest.fixture
def db(monkeypatch):
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute(
        "CREATE TABLE assets(key TEXT PRIMARY KEY, name TEXT, description TEXT, "
        "metadata TEXT, searchable_text TEXT, embedding TEXT)"
    )
    con.create_function("vector32", 1, lambda value: value)
    con.create_function("vector_distance_cos", 2, lambda a, b: 0.1)

    async def query(sql, args=None):
        return [dict(row) for row in con.execute(sql, args or [])]

    monkeypatch.setattr(server, "turso_query", query)

    async def embed(text):
        return [0.1, 0.2]

    monkeypatch.setattr(server, "voyage_embed", embed)
    yield con
    con.close()


def insert(db, ts, embedding="[0.1,0.2]"):
    metadata = {"thread_ts": str(ts), "channel_id": "C1", "key_topics": ["Kubernetes"]}
    db.execute(
        "INSERT INTO assets VALUES(?,?,?,?,?,?)",
        (
            f"slack://community/bot/B1/summary/C1/{ts}",
            "Kubernetes workers",
            "description",
            json.dumps(metadata),
            "Prefect Kubernetes workers",
            embedding,
        ),
    )


async def test_expired_populated_index_reports_unavailable(db):
    insert(db, time.time() - 200 * 86400)
    async with Client(server.mcp) as c:
        stats = await c.call_tool("get_stats", {})
        assert stats.data.total_threads == 1
        assert stats.data.searchable_threads == 0
        for tool in ("search", "similar"):
            result = await c.call_tool(tool, {"query": "Kubernetes"}, raise_on_error=False)
            assert result.is_error
            assert "refresh" in str(result.content).lower()


async def test_json_filters_accept_normal_json_whitespace_and_topic_case(db):
    insert(db, time.time())
    async with Client(server.mcp) as c:
        for tool in ("search", "similar"):
            result = await c.call_tool(
                tool, {"query": "Kubernetes", "topic": "kubernetes", "channel": "C1"}
            )
            assert len(result.data) == 1
            assert result.data[0].channel_id == "C1"


async def test_healthy_corpus_can_return_a_real_empty_search(db):
    insert(db, time.time())
    async with Client(server.mcp) as c:
        result = await c.call_tool("search", {"query": "not-in-this-index"})
        assert result.data == []
        assert not result.is_error


async def test_missing_embeddings_does_not_disguise_semantic_failure(db):
    insert(db, time.time(), embedding=None)
    async with Client(server.mcp) as c:
        result = await c.call_tool("similar", {"query": "Kubernetes"}, raise_on_error=False)
        assert result.is_error
        assert "embedding" in str(result.content).lower()
