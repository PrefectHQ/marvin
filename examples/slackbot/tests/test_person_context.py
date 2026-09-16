import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import tiktoken
from slackbot import api
from slackbot._internal import person_summary as summaries
from slackbot.slack import render_slack_context


@pytest.fixture(autouse=True)
def local_models(monkeypatch):
    model_settings = SimpleNamespace(utility_model="test")
    monkeypatch.setattr(api, "settings", model_settings)
    monkeypatch.setattr(summaries, "settings", model_settings)


def test_channel_evidence_preserves_authorship_and_excludes_future_and_current():
    history = [
        {
            "ts": "1.0",
            "user": "VICTORIA",
            "text": "Looking for developers to work with me",
        },
        {"ts": "2.0", "user": "OTHER", "text": "My deployment failed"},
        {"ts": "3.0", "user": "VICTORIA", "text": "get project from this"},
        {"ts": "4.0", "user": "OTHER", "text": "future message"},
    ]
    rendered = render_slack_context(history, [], "3.0", "3.0")
    assert "Looking for developers" in rendered
    assert '"author": "VICTORIA"' in rendered
    assert '"author": "OTHER"' in rendered
    assert "future message" not in rendered
    assert "get project from this" not in rendered


def test_thread_human_reply_and_deduplication():
    root = {"ts": "1.0", "user": "A", "text": "original question"}
    reply = {"ts": "2.0", "user": "B", "text": "correction without a mention"}
    rendered = render_slack_context([root], [root, reply], "1.0", "3.0")
    assert rendered.count("original question") == 1
    assert "correction without a mention" in rendered


def test_token_budget_handles_long_unbroken_and_unicode_text():
    encoding = tiktoken.get_encoding("cl100k_base")
    for text in ["x" * 100000, "你好世界" * 10000, "word " * 10000]:
        assert len(encoding.encode(summaries.bounded_context(text, 400))) <= 400


def test_person_scope_is_workspace_specific():
    assert summaries.summary_prefix("T1", "U1") != summaries.summary_prefix("T2", "U1")


async def test_interstitial_receives_summary_in_one_call(monkeypatch):
    run = AsyncMock(
        return_value=SimpleNamespace(output="A familiar orchestration puzzle.")
    )
    monkeypatch.setattr(api, "Agent", lambda **kwargs: SimpleNamespace(run=run))
    progress = SimpleNamespace(update=AsyncMock())
    await api._personality_blurb(
        progress, "hello", "Maintains Prefect", "mountain pika " * 300
    )
    payload = json.loads(run.call_args.args[0])
    assert payload["person_summary"] == "Maintains Prefect"
    assert payload["previous_answer"].startswith("mountain pika")
    assert (
        len(tiktoken.get_encoding("cl100k_base").encode(payload["previous_answer"]))
        <= 200
    )
    assert run.await_count == 1


async def test_no_change_does_not_write(monkeypatch):
    run = AsyncMock(return_value=SimpleNamespace(output=summaries.SummaryDecision()))
    monkeypatch.setattr(summaries, "Agent", lambda **kwargs: SimpleNamespace(run=run))
    save = AsyncMock()
    monkeypatch.setattr(summaries.PersonSummary, "save", save)
    await summaries.update_person_summary(
        "T1", "U1", "C1", "1788929066.452399", "prior", "hi"
    )
    save.assert_not_awaited()
    data = json.loads(run.call_args.args[0])
    assert set(data) == {"prior_summary", "date", "user_message"}


async def test_changed_summary_persists_timestamped_bounded_snapshot(monkeypatch):
    run = AsyncMock(
        return_value=SimpleNamespace(
            output=summaries.SummaryDecision(summary="new " * 1000)
        )
    )
    monkeypatch.setattr(summaries, "Agent", lambda **kwargs: SimpleNamespace(run=run))
    saved = []

    async def save(self, name, **kwargs):
        saved.append((self, name))

    @asynccontextmanager
    async def client():
        yield SimpleNamespace(
            request=AsyncMock(return_value=SimpleNamespace(json=lambda: []))
        )

    monkeypatch.setattr(summaries.PersonSummary, "save", save)
    monkeypatch.setattr(summaries, "get_client", client)
    await summaries.update_person_summary(
        "T1", "U1", "C1", "1788929066.452399", "prior", "hi"
    )
    block, name = saved[0]
    assert name.endswith("001788929066-452399")
    assert block.channel_id == "C1"
    assert len(tiktoken.get_encoding("cl100k_base").encode(block.summary)) <= 400


async def test_summary_failure_is_nonfatal_and_unknown_user_skipped(monkeypatch):
    run = AsyncMock(side_effect=RuntimeError("unavailable"))
    monkeypatch.setattr(summaries, "Agent", lambda **kwargs: SimpleNamespace(run=run))
    await summaries.update_person_summary("T1", "unknown", "C1", "1.0", "", "hi")
    run.assert_not_awaited()
    await summaries.update_person_summary("T1", "U1", "C1", "1.0", "", "hi")
    assert run.await_count == 1


async def test_legacy_system_context_is_not_replayed(monkeypatch):
    from pydantic_ai.messages import (
        ModelMessagesTypeAdapter,
        ModelRequest,
        SystemPromptPart,
        UserPromptPart,
    )
    from slackbot._internal.message_store import ChatHistoryBlock, MessageStore

    messages = [
        ModelRequest(parts=[SystemPromptPart("old user's profile")]),
        ModelRequest(parts=[UserPromptPart("original question")]),
    ]
    monkeypatch.setattr(
        ChatHistoryBlock,
        "aload",
        AsyncMock(
            return_value=SimpleNamespace(
                messages_json=ModelMessagesTypeAdapter.dump_json(messages).decode()
            )
        ),
    )
    history = await MessageStore().get("1.0")
    assert len(history) == 1
    assert history[0].parts[0].content == "original question"


async def test_summary_read_uses_literal_prefix_and_preserves_clear(monkeypatch):
    from contextlib import asynccontextmanager

    request = AsyncMock(
        return_value=SimpleNamespace(json=lambda: [{"data": {"summary": ""}}])
    )

    @asynccontextmanager
    async def client():
        yield SimpleNamespace(request=request)

    monkeypatch.setattr(summaries, "get_client", client)
    assert await summaries.load_person_summary("T1", "U1") == ""
    query = request.call_args.kwargs["json"]
    assert query["block_documents"]["name"]["like_"] == summaries.summary_prefix(
        "T1", "U1"
    )
    assert query["limit"] == 1
    assert query["sort"] == "NAME_DESC"
