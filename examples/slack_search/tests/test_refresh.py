import sqlite3
import time
from types import SimpleNamespace

import backfill_asset_embeddings as backfill
import index_assets as index
import pytest


@pytest.fixture
def db(monkeypatch):
    con = sqlite3.connect(":memory:", check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.create_function("vector32", 1, lambda value: value)
    con.execute(
        "CREATE TABLE assets(key TEXT PRIMARY KEY, type TEXT, name TEXT, description TEXT, "
        "owners TEXT, last_seen TEXT, metadata TEXT, searchable_text TEXT, embedding TEXT)"
    )

    def query(settings, sql, args=None):
        return [dict(row) for row in con.execute(sql, args or [])]

    def write(settings, statements, *args):
        for sql, params in statements:
            con.execute(sql, params or [])

    monkeypatch.setattr(index, "turso_batch_exec", write)
    monkeypatch.setattr(backfill, "turso_batch_exec", write)
    monkeypatch.setattr(backfill, "turso_query", query)
    yield con
    con.close()


def asset(ts, summary="Kubernetes worker setup"):
    return {
        "key": f"slack://community/bot/B1/summary/C1/{ts}",
        "properties": {"name": "Kubernetes", "description": "Thread summary"},
        "latest_materialization": {
            "metadata": {"thread_ts": str(ts), "summary": summary, "key_topics": ["kubernetes"]}
        },
    }


async def test_current_summary_rejects_raw_assets_and_invalid_dates():
    cutoff = time.time() - 90 * 86400
    assert index.current_summary(asset(time.time()), cutoff)
    assert not index.current_summary(asset(cutoff - 1), cutoff)
    assert not index.current_summary(asset("not a timestamp"), cutoff)
    assert not index.current_summary({"key": "slack://community/bot/B1/facts/U1"}, cutoff)


def test_refresh_populates_search_and_reuses_unchanged_embeddings(db, monkeypatch):
    current = asset(time.time())
    old = asset(time.time() - 200 * 86400)

    async def list_assets(**kwargs):
        return [current, old, {"key": "slack://community/bot/B1"}]

    monkeypatch.setattr(index, "list_assets", list_assets)
    calls = []

    def embed(settings, texts):
        calls.extend(texts)
        return [[0.1, 0.2] for _ in texts]

    monkeypatch.setattr(backfill, "voyage_embed", embed)
    settings = SimpleNamespace()
    index.cmd_refresh(settings)
    row = dict(db.execute("SELECT * FROM assets").fetchone())
    assert row["key"] == current["key"]
    assert row["embedding"] is not None
    assert len(calls) == 1
    index.cmd_refresh(settings)
    assert len(calls) == 1
    current["latest_materialization"]["metadata"]["summary"] = "Corrected worker setup"
    index.cmd_refresh(settings)
    assert len(calls) == 2
    assert "Corrected" in calls[-1]
    assert db.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 1


def test_dry_run_writes_nothing(db, monkeypatch):
    async def list_assets(**kwargs):
        return [asset(time.time())]

    monkeypatch.setattr(index, "list_assets", list_assets)
    monkeypatch.setattr(
        backfill, "voyage_embed", lambda *args: pytest.fail("embedded during dry run")
    )
    index.cmd_refresh(SimpleNamespace(), dry_run=True)
    assert db.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0


def test_backfill_does_not_attach_embedding_to_changed_text(db, monkeypatch):
    row = index.asset_to_row(asset(time.time()))
    db.execute(
        "INSERT INTO assets(key,type,name,description,owners,last_seen,metadata,searchable_text) "
        "VALUES(?,?,?,?,?,?,?,?)",
        row,
    )

    def embed(settings, texts):
        db.execute("UPDATE assets SET searchable_text='changed during embedding'")
        return [[0.1, 0.2]]

    monkeypatch.setattr(backfill, "voyage_embed", embed)
    backfill.backfill_embeddings(SimpleNamespace())
    assert db.execute("SELECT embedding FROM assets").fetchone()[0] is None
