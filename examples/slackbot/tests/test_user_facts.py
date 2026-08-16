"""Regression tests for the user-facts pipeline fixes."""

from slackbot._internal.personalization import _annotate_row
from slackbot._internal.vectors import (
    DELETE_MAX_DISTANCE,
    row_distance,
    select_rows_to_delete,
)
from slackbot.api import _extract_message_context
from slackbot.slack import SlackEvent


class FakeRow:
    def __init__(self, id: str, text: str, dist: float | None, created_at: str = ""):
        self.id = id
        self.text = text
        self.created_at = created_at
        self._dist = dist

    def __getitem__(self, key: str) -> float:
        if key == "$dist" and self._dist is not None:
            return self._dist
        raise KeyError(key)


class TestRowDistance:
    def test_reads_dist_key(self):
        assert row_distance(FakeRow("a", "x", 0.42)) == 0.42

    def test_missing_dist_is_none(self):
        assert row_distance(FakeRow("a", "x", None)) is None


class TestSelectRowsToDelete:
    def test_only_deletes_within_threshold(self):
        rows = [
            FakeRow("close", "user uses k8s", DELETE_MAX_DISTANCE - 0.1),
            FakeRow("far", "user likes coffee", DELETE_MAX_DISTANCE + 0.1),
            FakeRow("no-dist", "user is on gcp", None),
        ]
        assert select_rows_to_delete(rows) == [("close", "user uses k8s")]

    def test_empty_rows(self):
        assert select_rows_to_delete([]) == []


class TestAnnotateRow:
    def test_appends_stored_date(self):
        row = FakeRow("a", "user uses Prefect 3.x", None, "2026-08-15T01:02:03+00:00")
        assert _annotate_row(row) == "user uses Prefect 3.x (stored 2026-08-15)"

    def test_no_created_at(self):
        assert _annotate_row(FakeRow("a", "user uses Prefect 3.x", None)) == (
            "user uses Prefect 3.x"
        )

    def test_empty_text(self):
        assert _annotate_row(FakeRow("a", "  ", None, "2026-08-15")) == ""


class TestAuthorExtraction:
    def test_app_mention_author_is_event_user(self):
        event = SlackEvent(
            type="app_mention",
            user="U123",
            text="<@UBOT> hi",
            ts="1.0",
            event_ts="1.0",
            channel="C1",
        )
        *_, author = _extract_message_context(event)
        assert author == "U123"

    def test_edit_author_comes_from_nested_message(self):
        event = SlackEvent(
            type="message",
            subtype="message_changed",
            message={"user": "U456", "ts": "1.0", "text": "<@UBOT> edited"},
            ts="2.0",
            event_ts="2.0",
            channel="C1",
        )
        *_, author = _extract_message_context(event)
        assert author == "U456"

    def test_missing_author_is_none(self):
        event = SlackEvent(
            type="message",
            subtype="message_changed",
            message={"ts": "1.0", "text": "hi"},
            ts="2.0",
            event_ts="2.0",
            channel="C1",
        )
        *_, author = _extract_message_context(event)
        assert author is None
