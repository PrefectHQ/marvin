"""Migration script to normalize topic labels in Turso."""

import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

NORMALIZATION_MAP: dict[str, str] = {
    # deployments (general)
    "prefect 3.x deployment": "deployments",
    "prefect deployment": "deployments",
    "prefect 3.x deployments": "deployments",
    "prefect deployments": "deployments",
    "flow deployment": "deployments",
    # prefect.yaml
    "prefect.yaml configuration": "prefect.yaml",
    "prefect yaml configuration": "prefect.yaml",
    # environment variables
    "environment variable configuration": "environment variables",
    # concurrency (general)
    "concurrency limits": "concurrency",
    "prefect 3.x concurrency limits": "concurrency",
    "concurrency management": "concurrency",
    "prefect 3.x concurrency management": "concurrency",
    # work pools
    "work pools and workers": "work pools",
    "prefect 3.x work pools": "work pools",
    # kubernetes
    "kubernetes deployment": "kubernetes",
    # automations
    "prefect 3.x automations": "automations",
    # prefect version tags (remove version specificity)
    "prefect 3.x": "prefect 3.x",  # keep this one as canonical
    "prefect 2.x": "prefect 2.x",  # keep this one as canonical
}


def get_turso_client() -> tuple[str, str]:
    turso_url = os.environ.get("TURSO_URL", "").strip().strip('"')
    turso_token = os.environ.get("TURSO_TOKEN", "").strip().strip('"')
    if turso_url.startswith("libsql://"):
        turso_url = turso_url[len("libsql://") :]
    return turso_url, turso_token


def turso_query(host: str, token: str, sql: str, args: list | None = None) -> list[dict]:
    stmt: dict = {"sql": sql}
    if args:
        stmt["args"] = [{"type": "text", "value": str(a)} for a in args]

    resp = httpx.post(
        f"https://{host}/v2/pipeline",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    result = data["results"][0]
    if result["type"] == "error":
        raise Exception(f"Turso error: {result['error']}")

    cols = [c["name"] for c in result["response"]["result"]["cols"]]
    rows = result["response"]["result"]["rows"]

    def extract(cell):
        if cell is None:
            return None
        if isinstance(cell, dict):
            return cell.get("value")
        return cell

    return [dict(zip(cols, [extract(c) for c in row])) for row in rows]


def normalize_topics(topics: list[str]) -> list[str]:
    """Normalize a list of topics, preserving order and deduping."""
    seen = set()
    result = []
    for t in topics:
        normalized = NORMALIZATION_MAP.get(t.lower().strip(), t.lower().strip())
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def main(apply: bool = False):
    host, token = get_turso_client()

    # fetch all rows with key_topics
    print("fetching rows with key_topics...")
    rows = turso_query(
        host,
        token,
        """
        SELECT key, metadata FROM assets
        WHERE metadata LIKE '%key_topics%'
    """,
    )
    print(f"found {len(rows)} rows")

    updates = []
    for row in rows:
        key = row["key"]
        meta_raw = row["metadata"]
        if not meta_raw:
            continue

        meta = json.loads(meta_raw)
        old_topics = meta.get("key_topics", [])
        if not old_topics:
            continue

        new_topics = normalize_topics(old_topics)

        if old_topics != new_topics:
            meta["key_topics"] = new_topics
            updates.append((key, json.dumps(meta)))

    print(f"found {len(updates)} rows to update")

    if not updates:
        print("nothing to do")
        return

    # preview first 10
    print("\npreview (first 10):")
    for key, new_meta in updates[:10]:
        meta = json.loads(new_meta)
        print(f"  {meta['key_topics']}")

    if not apply:
        print("\ndry run - pass --apply to execute updates")
        return

    # execute updates
    print(f"\nupdating {len(updates)} rows...")
    for i, (key, new_meta) in enumerate(updates):
        turso_query(host, token, "UPDATE assets SET metadata = ? WHERE key = ?", [new_meta, key])
        print(f"\r  {i + 1}/{len(updates)}", end="", flush=True)
    print()

    print(f"done - updated {len(updates)} rows")


if __name__ == "__main__":
    import sys

    main(apply="--apply" in sys.argv)
