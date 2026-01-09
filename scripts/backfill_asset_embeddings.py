#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx", "pydantic-settings"]
# ///
"""
Backfill embeddings for indexed Prefect assets in Turso.

Uses Voyage AI to generate embeddings for semantic search.

## Prerequisites

- Assets must be synced to Turso (run `./scripts/index_assets.py sync` first)
- VOYAGE_API_KEY environment variable set

## Usage

```bash
# Process all assets missing embeddings
./scripts/backfill_asset_embeddings.py

# Process limited batch
./scripts/backfill_asset_embeddings.py --limit 100

# Preview without changes
./scripts/backfill_asset_embeddings.py --dry-run

# Adjust batch size (default 20)
./scripts/backfill_asset_embeddings.py --batch-size 10
```

## Environment Variables

- TURSO_URL: Turso database URL
- TURSO_TOKEN: Turso auth token
- VOYAGE_API_KEY: Voyage AI API key

## Embedding Model

Uses `voyage-3-lite` (512 dimensions) for efficient document embeddings.
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
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


def turso_batch_exec(
    settings: Settings, statements: list[tuple[str, list | None]], retries: int = 3
) -> None:
    """Execute multiple statements in a single pipeline request."""
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
            for i, result in enumerate(data["results"][:-1]):
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
            "input_type": "document",
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return [item["embedding"] for item in data["data"]]


def main():
    parser = argparse.ArgumentParser(
        description="Backfill embeddings for indexed assets"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Max assets to process (0 = all)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=20, help="Assets per Voyage API call"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without changes"
    )
    args = parser.parse_args()

    try:
        settings = Settings()  # type: ignore
    except Exception as e:
        print(f"error loading settings: {e}", file=sys.stderr)
        print(
            "required env vars: TURSO_URL, TURSO_TOKEN, VOYAGE_API_KEY", file=sys.stderr
        )
        sys.exit(1)

    # Get assets needing embeddings
    sql = """
        SELECT key, name, searchable_text
        FROM assets
        WHERE embedding IS NULL
    """
    params: list | None = None
    if args.limit > 0:
        sql += " LIMIT ?"
        params = [args.limit]
    assets = turso_query(settings, sql, params)

    if not assets:
        print("no assets need embeddings")
        return

    print(f"found {len(assets)} assets needing embeddings")

    if args.dry_run:
        for asset in assets[:10]:
            name = asset.get("name") or asset["key"][:60]
            print(f"  - {name}")
        if len(assets) > 10:
            print(f"  ... and {len(assets) - 10} more")
        return

    def process_batch(batch_info):
        batch_num, batch = batch_info
        # Use searchable_text for embedding, fallback to name + key
        texts = []
        for asset in batch:
            text = asset.get("searchable_text") or ""
            if not text.strip():
                text = f"{asset.get('name', '')} {asset['key']}"
            # Truncate to 8000 chars - well within Voyage API's input limits
            texts.append(text[:8000])

        embeddings = voyage_embed(settings, texts)
        statements = []
        for asset, embedding in zip(batch, embeddings):
            embedding_json = json.dumps(embedding)
            statements.append(
                (
                    "UPDATE assets SET embedding = vector32(?) WHERE key = ?",
                    [embedding_json, asset["key"]],
                )
            )
        turso_batch_exec(settings, statements)
        return batch_num, len(batch)

    batches = [
        (i // args.batch_size + 1, assets[i : i + args.batch_size])
        for i in range(0, len(assets), args.batch_size)
    ]

    processed = 0
    workers = min(8, len(batches))
    print(f"processing {len(batches)} batches with {workers} workers...")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_batch, b): b[0] for b in batches}
        for future in as_completed(futures):
            batch_num, count = future.result()
            processed += count
            print(f"batch {batch_num} done ({processed}/{len(assets)})", flush=True)

    print(f"done! processed {processed} assets")


if __name__ == "__main__":
    main()
