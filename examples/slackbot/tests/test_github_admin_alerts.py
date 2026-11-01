"""GitHub failures the agent can't fix must reach the admin, not just the user.

A dead GitHub token once surfaced only as Marvin telling a community member
"my GitHub issue search is failing authentication" — the issue tool swallowed
the error without notifying anyone.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from pydantic_ai.models.test import TestModel
from slackbot import core
from slackbot.github import GitHubAuthError, GitHubError, GitHubRateLimitError
from slackbot.settings import settings

CTX = SimpleNamespace(
    deps={
        "workspace_name": "prefect-community",
        "channel_id": "C123",
        "thread_ts": "1730000000.000100",
        "user_id": "U999",
    }
)


@pytest.fixture
def issue_tool(monkeypatch):
    monkeypatch.setattr(core, "get_run_logger", Mock())
    monkeypatch.setattr(core, "_base_system_prompt", lambda: "")
    monkeypatch.setattr(settings, "admin_slack_user_id", "UADMIN")
    agent = core.create_agent(model=TestModel())
    return agent._function_toolset.tools["read_github_issues"].function


@pytest.fixture
def sent(monkeypatch) -> AsyncMock:
    send = AsyncMock()
    monkeypatch.setattr(core, "_send_admin_notification", send)
    return send


@pytest.mark.parametrize(
    "error", [GitHubAuthError("GitHub authentication failed"), GitHubError("boom")]
)
async def test_issue_search_failure_notifies_admin(
    monkeypatch, issue_tool, sent, error
):
    monkeypatch.setattr(core, "search_issues", AsyncMock(side_effect=error))

    reply = await issue_tool(CTX, "23681")

    sent.assert_awaited_once()
    assert str(error) in sent.await_args.args[0]
    assert "<@UADMIN> has been notified" in reply


async def test_rate_limit_does_not_page_admin(monkeypatch, issue_tool, sent):
    monkeypatch.setattr(
        core, "search_issues", AsyncMock(side_effect=GitHubRateLimitError("slow"))
    )

    await issue_tool(CTX, "23681")

    sent.assert_not_awaited()


async def test_slack_ok_false_is_an_error(monkeypatch):
    monkeypatch.setattr(settings, "admin_slack_user_id", "UADMIN")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"ok": False, "error": "channel_not_found"}
        )
    )
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        core.httpx, "AsyncClient", lambda: real_client(transport=transport)
    )

    with pytest.raises(RuntimeError, match="channel_not_found"):
        await core._send_admin_notification("hi")


async def test_failed_admin_notification_does_not_break_the_tool(monkeypatch):
    monkeypatch.setattr(settings, "admin_slack_user_id", "UADMIN")
    monkeypatch.setattr(
        core,
        "_send_admin_notification",
        AsyncMock(side_effect=RuntimeError("Slack chat.postMessage failed")),
    )

    await core._notify_admin_about_error(CTX, "GitHub authentication failed")
