import json
from types import SimpleNamespace
from unittest.mock import patch

from slackbot._internal.personalization import load_personalization_snapshot
from slackbot._internal.prompting import _build_personalization_section
from turbopuffer.types import NamespaceMetadata


def test_small_profile_preserves_qualifications_and_legacy_rows_without_embedding():
    text = "Testing Prefect 3; production still uses 2.20.16."
    with patch("slackbot._internal.personalization.TurboPuffer") as factory:
        store = factory.return_value.__enter__.return_value
        # Use the real SDK model: `schema` is a Pydantic method, while the
        # server's JSON schema field is exposed as `schema_`.
        store.ns.metadata.return_value = NamespaceMetadata.model_validate(
            {
                "approx_row_count": 1,
                "approx_logical_bytes": 100,
                "created_at": "2026-09-08T00:00:00Z",
                "updated_at": "2026-09-08T00:00:00Z",
                "schema": {"text": {"type": "string"}},
            }
        )
        store.ns.query.return_value = SimpleNamespace(
            rows=[SimpleNamespace(id="a", text=text)]
        )
        snapshot = load_personalization_snapshot("user-facts-U1", "Which version?")
        store.query.assert_not_called()
    assert json.loads(snapshot.profile_summary) == {"id": "a", "text": text}
    assert snapshot.seen_before
    assert not snapshot.relevant_notes
    assert store.ns.query.call_args.kwargs["rank_by"] == ("id", "desc")
    assert store.ns.query.call_args.kwargs["filters"] is None


def test_recall_filters_superseded_versions_and_preserves_sources():
    row = SimpleNamespace(
        id="b",
        text="Now uses Prefect 3.",
        created_at="2026-09-08",
        supersedes="a",
        channel_id="C1",
        thread_ts="1.0",
        correction_reason="User reported completing the migration.",
    )
    with patch("slackbot._internal.personalization.TurboPuffer") as factory:
        store = factory.return_value.__enter__.return_value
        store.ns.metadata.return_value = SimpleNamespace(
            schema_={"created_at": {}, "superseded_by": {}}
        )
        store.ns.query.return_value = SimpleNamespace(rows=[row])
        snapshot = load_personalization_snapshot("user-facts-U1", "Hi")
    assert store.ns.query.call_args.kwargs["filters"] == ("superseded_by", "Eq", None)
    fact = json.loads(snapshot.profile_summary)
    assert fact["supersedes"] == "a"
    assert fact["correction_reason"] == row.correction_reason
    assert fact["channel_id"] == "C1"


def test_unavailable_memory_does_not_assert_new_user():
    with patch(
        "slackbot._internal.personalization.TurboPuffer",
        side_effect=RuntimeError("offline"),
    ):
        snapshot = load_personalization_snapshot("user-facts-U1", "Hi")
    prompt = _build_personalization_section(
        {
            "user_profile": snapshot.profile_summary,
            "user_notes": snapshot.relevant_notes,
            "seen_before": snapshot.seen_before,
            "memory_warning": snapshot.memory_warning,
        }
    )
    assert "unavailable" in prompt
    assert "No stored facts found" not in prompt


def test_failed_older_search_keeps_profile_and_reports_incomplete_retrieval():
    with patch("slackbot._internal.personalization.TurboPuffer") as factory:
        store = factory.return_value.__enter__.return_value
        store.ns.metadata.return_value = SimpleNamespace(schema_={"created_at": {}})
        store.ns.query.return_value = SimpleNamespace(
            rows=[SimpleNamespace(id=str(i), text=f"fact {i}") for i in range(26)]
        )
        store.query.side_effect = RuntimeError("embedding unavailable")
        snapshot = load_personalization_snapshot("user-facts-U1", "old context")
    assert len(snapshot.profile_summary.splitlines()) == 25
    assert "incomplete" in snapshot.memory_warning
    assert snapshot.seen_before
