#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["prefect", "httpx", "pydantic-settings"]
# ///
"""
Asset indexing script for Prefect Cloud -> Turso.

This script syncs Prefect Cloud assets to a Turso database for efficient
querying via SQL or semantic search (embeddings can be backfilled separately).

## Prerequisites

- uv must be installed
- You must be authenticated to Prefect Cloud
- You must have a workspace selected
- Turso database credentials (TURSO_URL, TURSO_TOKEN)

## Setup

1. Create a Turso database:
   ```bash
   turso db create marvin-assets
   turso db tokens create marvin-assets
   ```

2. Set environment variables:
   ```bash
   export TURSO_URL="libsql://marvin-assets-<username>.turso.io"
   export TURSO_TOKEN="<your-token>"
   ```

## Usage

### Initialize schema
```bash
./scripts/index_assets.py init
```

### Sync assets to Turso
```bash
./scripts/index_assets.py sync                    # full sync
./scripts/index_assets.py sync --limit 100        # sync first 100 assets
./scripts/index_assets.py sync --dry-run          # preview what would be synced
```

### Query assets
```bash
./scripts/index_assets.py query "SELECT * FROM assets WHERE type = 'slack' LIMIT 5"
./scripts/index_assets.py query "SELECT COUNT(*) FROM assets GROUP BY type"
```

### Search assets
```bash
./scripts/index_assets.py search "concurrency limits"
./scripts/index_assets.py search "dbt model" --type duckdb
```

### Stats
```bash
./scripts/index_assets.py stats
```

## Schema

The `assets` table stores:
- `key`: Unique asset identifier (e.g., `slack://workspace/...`)
- `type`: Asset type derived from URI prefix (slack, duckdb, etc.)
- `name`: Human-readable name from properties
- `description`: Asset description
- `owners`: JSON array of owners
- `last_seen`: Last seen timestamp
- `metadata`: Full metadata JSON blob
- `searchable_text`: Combined text for full-text search
- `embedding`: F32_BLOB(512) for semantic search (nullable, backfill separately)
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any

import httpx
from prefect import get_client
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"), extra="ignore"
    )

    turso_url: str
    turso_token: str
    voyage_api_key: str

    @property
    def turso_host(self) -> str:
        """Strip libsql:// prefix if present."""
        url = self.turso_url
        if url.startswith("libsql://"):
            url = url[len("libsql://") :]
        return url


# --- Turso operations ---


def turso_query(settings: Settings, sql: str, args: list | None = None) -> list[dict]:
    """Execute a query against Turso and return rows."""
    stmt = {"sql": sql}
    if args:
        stmt["args"] = [{"type": "text", "value": str(a)} for a in args]

    response = httpx.post(
        f"https://{settings.turso_host}/v2/pipeline",
        headers={
            "Authorization": f"Bearer {settings.turso_token}",
            "Content-Type": "application/json",
        },
        json={"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    try:
        result = data["results"][0]
        if result["type"] == "error":
            raise Exception(f"Turso error: {result['error']}")

        cols = [c["name"] for c in result["response"]["result"]["cols"]]
        rows = result["response"]["result"]["rows"]

        def extract_value(cell):
            if cell is None:
                return None
            if isinstance(cell, dict):
                return cell.get("value")
            return cell

        return [dict(zip(cols, [extract_value(cell) for cell in row])) for row in rows]
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"malformed Turso response: {e}") from e


def turso_exec(
    settings: Settings, sql: str, args: list | None = None, retries: int = 3
) -> None:
    """Execute a statement against Turso with retry logic."""
    turso_batch_exec(settings, [(sql, args)], retries)


def turso_batch_exec(
    settings: Settings, statements: list[tuple[str, list | None]], retries: int = 3
) -> None:
    """Execute multiple statements in a single pipeline request."""
    import time

    requests = []
    for sql, args in statements:
        stmt = {"sql": sql}
        if args:
            stmt["args"] = [{"type": "text", "value": str(a)} for a in args]
        requests.append({"type": "execute", "stmt": stmt})
    requests.append({"type": "close"})

    for attempt in range(retries):
        try:
            response = httpx.post(
                f"https://{settings.turso_host}/v2/pipeline",
                headers={
                    "Authorization": f"Bearer {settings.turso_token}",
                    "Content-Type": "application/json",
                },
                json={"requests": requests},
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            for i, result in enumerate(data["results"][:-1]):  # skip close result
                if result["type"] == "error":
                    raise Exception(f"Turso error on statement {i}: {result['error']}")
            return
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError) as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  {type(e).__name__}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


# --- Prefect asset operations ---


async def list_assets(
    limit: int = 0, asset_type: str = "slack"
) -> list[dict[str, Any]]:
    """List assets from Prefect Cloud, filtered by type."""
    print(f"  fetching assets from Prefect Cloud (type={asset_type})...", flush=True)

    async with get_client() as client:
        response = await client._client.get(
            "/assets/", params={"limit": 10000, "offset": 0}
        )
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            assets = data
        else:
            assets = data.get("results", [])

        print(f"  fetched {len(assets)} total assets", flush=True)

        # Filter by type
        if asset_type:
            assets = [
                a for a in assets if extract_asset_type(a.get("key", "")) == asset_type
            ]
            print(f"  filtered to {len(assets)} {asset_type} assets", flush=True)

        if limit > 0:
            assets = assets[:limit]

    return assets


def extract_asset_type(key: str) -> str:
    """Extract asset type from URI key."""
    if "://" in key:
        return key.split("://")[0]
    return "other"


def build_searchable_text(asset: dict) -> str:
    """Build combined searchable text from asset fields."""
    parts = []

    # Properties
    props = asset.get("properties", {})
    if props.get("name"):
        parts.append(props["name"])
    if props.get("description"):
        parts.append(props["description"])

    # Metadata from latest materialization
    meta = asset.get("latest_materialization", {}).get("metadata", {})
    if meta.get("title"):
        parts.append(meta["title"])
    if meta.get("summary"):
        parts.append(meta["summary"])
    if meta.get("key_topics"):
        parts.extend(meta["key_topics"])

    return " ".join(parts)


def asset_to_row(asset: dict) -> tuple:
    """Convert Prefect asset to database row values."""
    key = asset.get("key", "")
    asset_type = extract_asset_type(key)
    props = asset.get("properties", {})
    meta = asset.get("latest_materialization", {}).get("metadata", {})

    return (
        key,
        asset_type,
        props.get("name", ""),
        props.get("description", ""),
        json.dumps(props.get("owners", [])),
        asset.get("last_seen", ""),
        json.dumps(meta),
        build_searchable_text(asset),
    )


# --- Commands ---


def cmd_init(settings: Settings):
    """Initialize the database schema."""
    print("initializing schema...")

    schema = """
    CREATE TABLE IF NOT EXISTS assets (
        key TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        name TEXT,
        description TEXT,
        owners TEXT,
        last_seen TEXT,
        metadata TEXT,
        searchable_text TEXT,
        embedding F32_BLOB(512)
    );

    CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
    CREATE INDEX IF NOT EXISTS idx_assets_last_seen ON assets(last_seen);
    """

    for stmt in schema.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            turso_exec(settings, stmt)

    print("done!")


def cmd_sync(settings: Settings, limit: int = 0, dry_run: bool = False):
    """Sync assets from Prefect Cloud to Turso."""

    async def _sync():
        print("fetching assets from Prefect Cloud...")
        assets = await list_assets(limit=limit)
        print(f"found {len(assets)} assets")

        if dry_run:
            by_type = {}
            for asset in assets:
                t = extract_asset_type(asset.get("key", ""))
                by_type[t] = by_type.get(t, 0) + 1
            print("\nby type:")
            for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
                print(f"  {t}: {count}")
            print("\ndry run - no changes made")
            return

        # Batch upsert
        print("syncing to Turso...")
        batch_size = 50
        processed = 0

        for i in range(0, len(assets), batch_size):
            batch = assets[i : i + batch_size]
            statements = []

            for asset in batch:
                row = asset_to_row(asset)
                statements.append(
                    (
                        """
                    INSERT OR REPLACE INTO assets
                    (key, type, name, description, owners, last_seen, metadata, searchable_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        list(row),
                    )
                )

            turso_batch_exec(settings, statements)
            processed += len(batch)
            print(f"  synced {processed}/{len(assets)}")

        print(f"done! synced {processed} assets")

    asyncio.run(_sync())


def cmd_query(settings: Settings, sql: str):
    """Run a SQL query against the assets database."""
    rows = turso_query(settings, sql)
    if not rows:
        print("no results")
        return

    # Pretty print as JSON
    for row in rows:
        print(json.dumps(row, indent=2))


def cmd_search(settings: Settings, query: str, asset_type: str | None = None):
    """Search assets by text (simple LIKE-based search)."""
    sql = """
    SELECT key, type, name,
           SUBSTR(searchable_text, 1, 200) as preview
    FROM assets
    WHERE searchable_text LIKE ?
    """
    # Escape SQL LIKE special characters
    escaped_query = query.replace("%", r"\%").replace("_", r"\_")
    args = [f"%{escaped_query}%"]

    if asset_type:
        sql += " AND type = ?"
        args.append(asset_type)

    sql += " LIMIT 20"

    rows = turso_query(settings, sql, args)

    if not rows:
        print(f"no assets found matching '{query}'")
        return

    print(f"found {len(rows)} matching assets:\n")
    for row in rows:
        print(f"[{row['type']}] {row['name'] or row['key'][:60]}")
        if row.get("preview"):
            preview = row["preview"][:150].replace("\n", " ")
            print(f"  {preview}...")
        print()


def voyage_embed(settings: Settings, texts: list[str]) -> list[list[float]]:
    """Generate embeddings using Voyage AI."""
    response = httpx.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {settings.voyage_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "input": texts,
            "model": "voyage-3-lite",
            "input_type": "query",
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return [item["embedding"] for item in data["data"]]


def cmd_similar(
    settings: Settings, query: str, asset_type: str | None = None, limit: int = 10
):
    """Semantic search using embeddings."""
    # Get query embedding
    print(f"searching for: {query}")
    embeddings = voyage_embed(settings, [query])
    query_embedding = json.dumps(embeddings[0])

    # Vector similarity search
    sql = """
    SELECT key, type, name,
           SUBSTR(searchable_text, 1, 200) as preview,
           vector_distance_cos(embedding, vector32(?)) as distance
    FROM assets
    WHERE embedding IS NOT NULL
    """
    args = [query_embedding]

    if asset_type:
        sql += " AND type = ?"
        args.append(asset_type)

    sql += " ORDER BY distance LIMIT ?"
    args.append(limit)

    rows = turso_query(settings, sql, args)

    if not rows:
        print(
            "no assets with embeddings found (run backfill_asset_embeddings.py first)"
        )
        return

    print(f"\nfound {len(rows)} similar assets:\n")
    for row in rows:
        score = 1 - float(row.get("distance", 0))  # convert distance to similarity
        print(f"[{row['type']}] {row['name'] or row['key'][:60]} (score: {score:.3f})")
        if row.get("preview"):
            preview = row["preview"][:150].replace("\n", " ")
            print(f"  {preview}...")
        print()


def cmd_stats(settings: Settings):
    """Show database statistics."""
    print("asset statistics:\n")

    # Total count
    total = turso_query(settings, "SELECT COUNT(*) as count FROM assets")
    print(f"total assets: {total[0]['count']}")

    # By type
    by_type = turso_query(
        settings,
        "SELECT type, COUNT(*) as count FROM assets GROUP BY type ORDER BY count DESC",
    )
    print("\nby type:")
    for row in by_type:
        print(f"  {row['type']}: {row['count']}")

    # Embeddings
    with_embeddings = turso_query(
        settings, "SELECT COUNT(*) as count FROM assets WHERE embedding IS NOT NULL"
    )
    print(f"\nwith embeddings: {with_embeddings[0]['count']}")


def main():
    parser = argparse.ArgumentParser(
        description="Index Prefect Cloud assets to Turso",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="command to run")

    # init
    subparsers.add_parser("init", help="Initialize database schema")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Sync assets to Turso")
    sync_parser.add_argument(
        "--limit", type=int, default=0, help="Max assets to sync (0 = all)"
    )
    sync_parser.add_argument(
        "--dry-run", action="store_true", help="Preview without syncing"
    )

    # query
    query_parser = subparsers.add_parser("query", help="Run SQL query")
    query_parser.add_argument("sql", help="SQL query to execute")

    # search
    search_parser = subparsers.add_parser("search", help="Search assets by text")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--type", dest="asset_type", help="Filter by asset type")

    # similar (semantic search)
    similar_parser = subparsers.add_parser(
        "similar", help="Semantic search using embeddings"
    )
    similar_parser.add_argument("query", help="Search query")
    similar_parser.add_argument(
        "--type", dest="asset_type", help="Filter by asset type"
    )
    similar_parser.add_argument(
        "--limit", type=int, default=10, help="Max results (default: 10)"
    )

    # stats
    subparsers.add_parser("stats", help="Show database statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        settings = Settings()  # type: ignore
    except Exception as e:
        print(f"error loading settings: {e}", file=sys.stderr)
        print(
            "required env vars: TURSO_URL, TURSO_TOKEN, VOYAGE_API_KEY", file=sys.stderr
        )
        sys.exit(1)

    if args.command == "init":
        cmd_init(settings)
    elif args.command == "sync":
        cmd_sync(settings, args.limit, args.dry_run)
    elif args.command == "query":
        cmd_query(settings, args.sql)
    elif args.command == "search":
        cmd_search(settings, args.query, args.asset_type)
    elif args.command == "similar":
        cmd_similar(settings, args.query, args.asset_type, args.limit)
    elif args.command == "stats":
        cmd_stats(settings)


if __name__ == "__main__":
    main()
