"""distance thresholds and row helpers for the user-facts vector store.

thresholds are empirical, measured with text-embedding-3-small (cosine
distance): identical ~= 0.0, paraphrases ~= 0.12-0.15, contradictions
("Prefect 2.x" vs "Prefect 3.x") ~= 0.06 — *closer* than paraphrases, so
write-time dedup must be near-exact and contradiction handling stays with
the synthesis model. related question<->fact ~= 0.3, unrelated >= 0.68.
"""

from typing import Any

WRITE_DEDUP_MAX_DISTANCE = 0.03
DELETE_MAX_DISTANCE = 0.5
RELEVANCE_MAX_DISTANCE = 0.65


def row_distance(row: Any) -> float | None:
    try:
        return float(row["$dist"])
    except (KeyError, TypeError, ValueError):
        return None


def select_rows_to_delete(rows: list[Any]) -> list[tuple[str, str]]:
    """Pick (id, text) of rows close enough to the delete query to remove.

    Rows without a distance are kept (never deleted on missing evidence).
    """
    selected: list[tuple[str, str]] = []
    for row in rows:
        distance = row_distance(row)
        if distance is not None and distance <= DELETE_MAX_DISTANCE:
            selected.append((str(row.id), str(getattr(row, "text", ""))))
    return selected
