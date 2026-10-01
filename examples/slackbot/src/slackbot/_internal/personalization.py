"""Recall stored user accounts verbatim, preserving their provenance."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from raggy.vectorstores.tpuf import TurboPuffer
from turbopuffer import NotFoundError

from slackbot._internal.vectors import (
    RELEVANCE_MAX_DISTANCE,
    active_fact_filter,
    row_distance,
)

logger = logging.getLogger(__name__)
PROFILE_LIMIT = 25


@dataclass(frozen=True)
class PersonalizationSnapshot:
    seen_before: bool
    profile_summary: str
    relevant_notes: str
    memory_warning: str


def load_personalization_snapshot(
    namespace: str, user_question: str
) -> PersonalizationSnapshot:
    try:
        with TurboPuffer(namespace=namespace) as tpuf:
            try:
                metadata = tpuf.ns.metadata()
            except NotFoundError:
                return PersonalizationSnapshot(False, "", "", "")
            schema = metadata.schema_ or {}
            filters = active_fact_filter(schema)
            # Legacy namespaces may have no timestamps. Never name a missing
            # attribute in an order/filter: TPuf rejects it rather than ignoring it.
            order = "created_at" if "created_at" in schema else "id"
            rows = (
                tpuf.ns.query(
                    rank_by=(order, "desc"),
                    top_k=PROFILE_LIMIT + 1,
                    include_attributes=True,
                    filters=filters,
                ).rows
                or []
            )
            profile = rows[:PROFILE_LIMIT]
            warnings = []
            relevant = []
            if len(rows) > PROFILE_LIMIT:
                warnings.append(
                    f"Showing {PROFILE_LIMIT} stored facts; this is not the complete memory."
                )
                if user_question.strip():
                    try:
                        matches = (
                            tpuf.query(
                                user_question,
                                top_k=5,
                                include_attributes=True,
                                filters=filters,
                            ).rows
                            or []
                        )
                        known = {row.id for row in profile}
                        relevant = [
                            row
                            for row in matches
                            if row.id not in known
                            and (distance := row_distance(row)) is not None
                            and distance <= RELEVANCE_MAX_DISTANCE
                        ]
                    except Exception:
                        logger.warning(
                            "Relevant user-fact search failed for %s",
                            namespace,
                            exc_info=True,
                        )
                        warnings.append(
                            "Older fact retrieval is unavailable; the displayed notes are incomplete."
                        )
            if rows and not any(str(getattr(row, "text", "")).strip() for row in rows):
                warnings.append("Stored rows contained no usable fact text.")
            return PersonalizationSnapshot(
                seen_before=bool(rows),
                profile_summary="\n".join(filter(None, map(_annotate_row, profile))),
                relevant_notes="\n".join(filter(None, map(_annotate_row, relevant))),
                memory_warning="\n".join(warnings),
            )
    except Exception:
        logger.warning("User-fact store unavailable for %s", namespace, exc_info=True)
        return PersonalizationSnapshot(
            False,
            "",
            "",
            "User memory is unavailable; this does not mean no facts are stored.",
        )


def fact_record(row: Any) -> dict[str, Any]:
    """Public memory evidence, without its embedding or backend fields."""
    record = {"id": row.id, "text": getattr(row, "text", "")}
    for key in (
        "created_at",
        "thread_ts",
        "channel_id",
        "workspace_name",
        "supersedes",
        "superseded_by",
        "correction_reason",
    ):
        value = getattr(row, key, None)
        if value:
            record[key] = value
    return record


def _annotate_row(row: Any) -> str:
    if not str(getattr(row, "text", "")).strip():
        return ""
    # JSON quotes instructions embedded in notes and preserves their exact text.
    return json.dumps(fact_record(row), ensure_ascii=False)
