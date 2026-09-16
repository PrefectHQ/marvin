from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from slackbot.assets import correct_user_fact, delete_user_facts, read_user_fact


@pytest.fixture
def context():
    return {
        "user_id": "U1",
        "channel_id": "C1",
        "thread_ts": "2.0",
        "workspace_name": "community",
    }


async def test_correction_preserves_original_and_writes_successor_atomically(context):
    original = {
        "id": "old",
        "text": "Uses Prefect 2.",
        "created_at": "2026-08-01",
        "thread_ts": "1.0",
    }
    with (
        patch("slackbot.assets.read_user_fact", return_value=original),
        patch(
            "slackbot.assets.create_openai_embeddings",
            new=AsyncMock(return_value=[0.1, 0.2]),
        ),
        patch("slackbot.assets.TurboPuffer") as factory,
    ):
        result = await correct_user_fact(
            context, "old", "Uses Prefect 3 in staging only.", "User clarified scope."
        )
    write = factory.return_value.__enter__.return_value.ns.write
    write.assert_called_once()
    args = write.call_args.kwargs
    assert args["patch_rows"] == [{"id": "old", "superseded_by": result["fact"]["id"]}]
    replacement = args["upsert_rows"][0]
    assert replacement["text"] == "Uses Prefect 3 in staging only."
    assert replacement["supersedes"] == "old"
    assert replacement["thread_ts"] == "2.0"
    assert replacement["correction_reason"] == "User clarified scope."
    assert result["previous"] == original
    assert original["thread_ts"] == "1.0"


@pytest.mark.parametrize(
    "original,status",
    [
        (None, "not_found"),
        ({"id": "old", "text": "old", "superseded_by": "new"}, "superseded"),
    ],
)
async def test_correction_requires_a_current_fact_in_this_namespace(
    context, original, status
):
    with (
        patch("slackbot.assets.read_user_fact", return_value=original),
        patch("slackbot.assets.create_openai_embeddings") as embed,
    ):
        assert (await correct_user_fact(context, "old", "new", "clarified"))[
            "status"
        ] == status
        embed.assert_not_called()


async def test_fact_changed_during_embedding_is_not_overwritten(context):
    with (
        patch(
            "slackbot.assets.read_user_fact",
            side_effect=[{"id": "old", "text": "old"}, None],
        ),
        patch(
            "slackbot.assets.create_openai_embeddings",
            new=AsyncMock(return_value=[0.1]),
        ),
        patch("slackbot.assets.TurboPuffer") as factory,
    ):
        assert (await correct_user_fact(context, "old", "new", "clarified"))[
            "status"
        ] == "changed"
        factory.assert_not_called()


def test_exact_read_is_scoped_to_current_user(context):
    with patch("slackbot.assets.TurboPuffer") as factory:
        ns = factory.return_value.__enter__.return_value.ns
        ns.query.return_value = SimpleNamespace(rows=[])
        assert read_user_fact(context, "another-user-fact") is None
    factory.assert_called_once_with(namespace="user-facts-U1")
    assert ns.query.call_args.kwargs["filters"] == ("id", "Eq", "another-user-fact")


def test_forget_removes_entire_correction_chain(context):
    facts = {
        "a": {"text": "v1", "superseded_by": "b"},
        "b": {"text": "v2", "supersedes": "a", "superseded_by": "c"},
        "c": {"text": "v3", "supersedes": "b"},
    }
    with (
        patch("slackbot.assets.TurboPuffer") as factory,
        patch("slackbot.assets.select_rows_to_delete", return_value=[("b", "v2")]),
        patch(
            "slackbot.assets.read_user_fact",
            side_effect=lambda ctx, fact_id: facts[fact_id],
        ),
    ):
        deleted = delete_user_facts(context, "topic")
    assert dict(deleted) == {"a": "v1", "b": "v2", "c": "v3"}
    assert set(
        factory.return_value.__enter__.return_value.delete.call_args.args[0]
    ) == {"a", "b", "c"}
