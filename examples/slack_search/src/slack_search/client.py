"""Turso client for slack thread search."""

import os
from typing import Any

import httpx

TURSO_URL = os.environ.get("TURSO_URL", "").strip()
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "").strip()
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "").strip()


def _get_turso_host() -> str:
    """Strip libsql:// prefix if present."""
    url = TURSO_URL
    if url.startswith("libsql://"):
        url = url[len("libsql://") :]
    return url


async def turso_query(sql: str, args: list | None = None) -> list[dict[str, Any]]:
    """Execute a query against Turso and return rows."""
    if not TURSO_URL or not TURSO_TOKEN:
        raise RuntimeError("TURSO_URL and TURSO_TOKEN must be set")

    stmt: dict[str, Any] = {"sql": sql}
    if args:
        stmt["args"] = [{"type": "text", "value": str(a)} for a in args]

    payload = {"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]}
    url = f"https://{_get_turso_host()}/v2/pipeline"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {TURSO_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Turso HTTP {response.status_code} for {url}: {response.text}")
        data = response.json()

    result = data["results"][0]
    if result["type"] == "error":
        raise Exception(f"Turso error: {result['error']}")

    cols = [c["name"] for c in result["response"]["result"]["cols"]]
    rows = result["response"]["result"]["rows"]

    def extract_value(cell: Any) -> Any:
        if cell is None:
            return None
        if isinstance(cell, dict):
            return cell.get("value")
        return cell

    return [dict(zip(cols, [extract_value(cell) for cell in row])) for row in rows]


async def voyage_embed(text: str) -> list[float]:
    """Generate embedding for a query using Voyage AI."""
    if not VOYAGE_API_KEY:
        raise RuntimeError("VOYAGE_API_KEY must be set for semantic search")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {VOYAGE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "input": [text],
                "model": "voyage-3-lite",
                "input_type": "query",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

    return data["data"][0]["embedding"]
