"""Turso client for slack thread search."""

from functools import lru_cache
from typing import Any

import httpx
from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    turso_url: str = ""
    turso_token: str = ""
    voyage_api_key: str = ""

    @field_validator("turso_url", "turso_token", "voyage_api_key", mode="before")
    @classmethod
    def strip_quotes(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().strip('"').strip("'")
        return v

    @computed_field
    @property
    def turso_host(self) -> str:
        """Strip libsql:// prefix if present."""
        url = self.turso_url
        if url.startswith("libsql://"):
            url = url[len("libsql://") :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


async def turso_query(sql: str, args: list | None = None) -> list[dict[str, Any]]:
    """Execute a query against Turso and return rows."""
    settings = get_settings()
    if not settings.turso_url or not settings.turso_token:
        raise RuntimeError("TURSO_URL and TURSO_TOKEN must be set")

    stmt: dict[str, Any] = {"sql": sql}
    if args:
        stmt["args"] = [{"type": "text", "value": str(a)} for a in args]

    payload = {"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]}
    url = f"https://{settings.turso_host}/v2/pipeline"

    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {settings.turso_token}",
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
    settings = get_settings()
    if not settings.voyage_api_key:
        raise RuntimeError("VOYAGE_API_KEY must be set for semantic search")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {settings.voyage_api_key}",
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
