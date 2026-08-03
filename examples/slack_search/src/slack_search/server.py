"""MCP server for searching Prefect Slack thread summaries."""

from __future__ import annotations

import json
import time
from collections import Counter
from typing import Literal

import httpx
from fastmcp import FastMCP

from slack_search._types import SlackMessage, Stats, ThreadContent, ThreadDetail, ThreadSummary
from slack_search.client import get_settings, slack_get_thread, turso_query, voyage_embed

# slack retention policy - threads older than this are deleted
RETENTION_DAYS = 90

# -----------------------------------------------------------------------------
# load categories at import time for dynamic type generation
# -----------------------------------------------------------------------------


def _load_categories() -> dict[str, list[str]]:
    """Synchronously load categories from Turso at import time."""
    settings = get_settings()

    if not settings.turso_url or not settings.turso_token:
        return {"topics": [], "channels": []}

    try:
        resp = httpx.post(
            f"https://{settings.turso_host}/v2/pipeline",
            headers={
                "Authorization": f"Bearer {settings.turso_token}",
                "Content-Type": "application/json",
            },
            json={
                "requests": [
                    {
                        "type": "execute",
                        "stmt": {
                            "sql": """
                        SELECT metadata FROM assets
                        WHERE metadata LIKE '%key_topics%'
                        LIMIT 500
                    """
                        },
                    },
                    {"type": "close"},
                ]
            },
            timeout=30,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Turso HTTP {resp.status_code}: {resp.text}")
        data = resp.json()

        topics: Counter[str] = Counter()
        channels: Counter[str] = Counter()

        result = data["results"][0]
        if result["type"] != "error":
            for row in result["response"]["result"]["rows"]:
                meta_raw = row[0]
                if isinstance(meta_raw, dict):
                    meta_raw = meta_raw.get("value")
                if not meta_raw:
                    continue
                try:
                    meta = json.loads(meta_raw)
                    for topic in meta.get("key_topics", []):
                        if topic and topic.strip():
                            topics[topic.lower().strip()] += 1
                    channel = meta.get("channel_id")
                    if channel:
                        channels[channel] += 1
                except Exception:
                    pass

        return {
            "topics": [t for t, _ in topics.most_common(25)],
            "channels": [c for c, _ in channels.most_common(10)],
        }
    except Exception as e:
        print(f"warning: failed to load categories: {e}")
        return {"topics": [], "channels": []}


_categories = _load_categories()

# create dynamic Literal types from loaded data
if _categories["topics"]:
    TopicFilter = Literal.__getitem__(tuple(_categories["topics"]))
else:
    TopicFilter = str  # fallback if no data

if _categories["channels"]:
    ChannelFilter = Literal.__getitem__(tuple(_categories["channels"]))
else:
    ChannelFilter = str  # fallback


# -----------------------------------------------------------------------------
# server
# -----------------------------------------------------------------------------

mcp = FastMCP("slack-search")


# -----------------------------------------------------------------------------
# prompts
# -----------------------------------------------------------------------------


@mcp.prompt("usage_guide")
def usage_guide() -> str:
    """Instructions for using slack-search MCP tools."""
    topics_list = ", ".join(_categories["topics"][:5]) if _categories["topics"] else "none loaded"
    return f"""\
# slack-search MCP usage guide

search AI-generated summaries of Prefect Slack community threads.

## available filters

topics (top 5): {topics_list}
channels: {len(_categories["channels"])} available

## core tools

- `search(query, topic?, channel?)` - text search with optional filters
- `similar(query, topic?, channel?)` - semantic search using embeddings
- `get_thread(key)` - get full thread details
- `get_stats()` - get index statistics

## workflow

1. use `similar("your question")` to find semantically related threads
2. optionally filter by topic or channel
3. use `get_thread(key)` to get full details

## examples

- `similar("how to debug stuck flow runs")`
- `search("kubernetes", topic="prefect 3.x")`
- `similar("concurrency limits", channel="C04DZJC94DC")`
"""


# -----------------------------------------------------------------------------
# tools
# -----------------------------------------------------------------------------


def _retention_cutoff() -> float:
    """Unix timestamp for retention cutoff (now - RETENTION_DAYS)."""
    return time.time() - (RETENTION_DAYS * 24 * 60 * 60)


@mcp.tool
async def search(
    query: str,
    topic: TopicFilter | None = None,
    channel: ChannelFilter | None = None,
    limit: int = 5,
) -> list[ThreadSummary]:
    """text search across thread titles and summaries.

    searches for exact text matches in thread names and content.
    optionally filter by topic or channel.
    excludes threads older than 90 days (Slack retention policy).

    args:
        query: text to search for
        topic: filter by topic (see available topics in schema)
        channel: filter by channel ID
        limit: max results to return (default 5)

    returns:
        list of matching threads with name and preview
    """
    if not query:
        return []

    cutoff = _retention_cutoff()

    # build query with optional filters
    sql = """
        SELECT key, name, description, metadata,
               SUBSTR(searchable_text, 1, 300) as preview
        FROM assets
        WHERE searchable_text LIKE ?
          AND CAST(json_extract(metadata, '$.thread_ts') AS REAL) > ?
    """
    args: list = [f"%{query}%", cutoff]

    if topic:
        sql += " AND metadata LIKE ?"
        args.append(f'%"{topic}"%')

    if channel:
        sql += " AND metadata LIKE ?"
        args.append(f'%"channel_id":"{channel}"%')

    sql += " LIMIT ?"
    args.append(limit)

    rows = await turso_query(sql, args)

    return [
        ThreadSummary(
            key=row["key"],
            name=row["name"] or "",
            description=row["description"] or "",
            preview=row.get("preview", ""),
        )
        for row in rows
    ]


@mcp.tool
async def similar(
    query: str,
    topic: TopicFilter | None = None,
    channel: ChannelFilter | None = None,
    limit: int = 5,
) -> list[ThreadSummary]:
    """semantic search to find conceptually related threads.

    uses AI embeddings to find threads related to your query,
    even if they don't contain the exact words.
    optionally filter by topic or channel.
    excludes threads older than 90 days (Slack retention policy).

    args:
        query: what you're looking for (question or concept)
        topic: filter by topic (see available topics in schema)
        channel: filter by channel ID
        limit: max results to return (default 5)

    returns:
        list of similar threads with relevance scores
    """
    if not query:
        return []

    cutoff = _retention_cutoff()

    # get query embedding
    embedding = await voyage_embed(query)
    embedding_json = json.dumps(embedding)

    # build query with optional filters
    sql = """
        SELECT key, name, description, metadata,
               SUBSTR(searchable_text, 1, 300) as preview,
               vector_distance_cos(embedding, vector32(?)) as distance
        FROM assets
        WHERE embedding IS NOT NULL
          AND CAST(json_extract(metadata, '$.thread_ts') AS REAL) > ?
    """
    args: list = [embedding_json, cutoff]

    if topic:
        sql += " AND metadata LIKE ?"
        args.append(f'%"{topic}"%')

    if channel:
        sql += " AND metadata LIKE ?"
        args.append(f'%"channel_id":"{channel}"%')

    sql += " ORDER BY distance LIMIT ?"
    args.append(limit)

    rows = await turso_query(sql, args)

    return [
        ThreadSummary(
            key=row["key"],
            name=row["name"] or "",
            description=row["description"] or "",
            preview=row.get("preview", ""),
            score=1 - float(row.get("distance", 0)),
        )
        for row in rows
    ]


@mcp.tool
async def get_thread(key: str) -> ThreadDetail | None:
    """get full details of a thread by its key.

    retrieves complete thread information including:
    - full AI-generated summary
    - key topics discussed
    - message and participant counts
    - channel and workspace info

    args:
        key: the thread key (from search/similar results)

    returns:
        full thread details or None if not found
    """
    rows = await turso_query(
        """
        SELECT key, name, description, last_seen, metadata
        FROM assets
        WHERE key = ?
        """,
        [key],
    )

    if not rows:
        return None

    row = rows[0]
    metadata = json.loads(row.get("metadata", "{}") or "{}")

    return ThreadDetail(
        key=row["key"],
        name=row["name"] or "",
        description=row["description"] or "",
        last_seen=row.get("last_seen", ""),
        metadata=metadata,
    )


@mcp.tool
async def get_thread_messages(key: str) -> ThreadContent | None:
    """fetch actual messages from a Slack thread.

    retrieves the full conversation content from Slack's API,
    not just the AI summary. requires SLACK_API_TOKEN.

    args:
        key: the thread key (from search/similar results)

    returns:
        thread content with all messages, or None if not found
    """
    # parse key to get channel and thread_ts
    # key: slack://workspace/bot/BOT_ID/summary/CHANNEL_ID/THREAD_TS
    parts = key.split("/")
    if len(parts) < 8:
        return None

    workspace = parts[2]
    channel = parts[6]
    thread_ts = parts[7]

    messages = await slack_get_thread(channel, thread_ts)

    ts_clean = thread_ts.replace(".", "")
    url = f"https://{workspace}.slack.com/archives/{channel}/p{ts_clean}"

    return ThreadContent(
        channel_id=channel,
        thread_ts=thread_ts,
        url=url,
        messages=[
            SlackMessage(user=m.get("user", ""), text=m.get("text", ""), ts=m.get("ts", ""))
            for m in messages
        ],
        message_count=len(messages),
    )


@mcp.tool
async def get_stats() -> Stats:
    """get index statistics.

    returns:
        total thread count and embedding coverage
    """
    total = await turso_query("SELECT COUNT(*) as count FROM assets")
    with_emb = await turso_query("SELECT COUNT(*) as count FROM assets WHERE embedding IS NOT NULL")

    return Stats(
        total_threads=total[0]["count"],
        with_embeddings=with_emb[0]["count"],
    )


@mcp.tool
async def list_topics() -> list[str]:
    """list available topics for filtering.

    returns the top topics extracted from thread summaries.
    use these values with the `topic` parameter in search/similar.
    """
    return _categories["topics"]


@mcp.tool
async def list_channels() -> list[str]:
    """list available channels for filtering.

    returns channel IDs that have indexed threads.
    use these values with the `channel` parameter in search/similar.
    """
    return _categories["channels"]


# -----------------------------------------------------------------------------
# resources
# -----------------------------------------------------------------------------


@mcp.resource("slack-search://stats")
async def stats_resource() -> str:
    """Current index statistics."""
    stats = await get_stats()
    return f"slack search: {stats.total_threads} threads ({stats.with_embeddings} with embeddings)"


@mcp.resource("slack-search://topics")
def topics_resource() -> str:
    """Available topics for filtering."""
    return "\n".join(_categories["topics"])


@mcp.resource("slack-search://channels")
def channels_resource() -> str:
    """Available channels for filtering."""
    return "\n".join(_categories["channels"])


# -----------------------------------------------------------------------------
# entrypoint
# -----------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
