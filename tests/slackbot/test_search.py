import os

import pytest

os.environ.setdefault("MARVIN_SLACKBOT_SLACK_API_TOKEN", "test-token")

from slackbot.github import GitHubAuthError, GitHubRateLimitError
from slackbot.search import _read_github_issues_async


@pytest.mark.asyncio
async def test_read_github_issues_returns_auth_message(monkeypatch):
    async def fake_search_issues(*args, **kwargs):
        raise GitHubAuthError("GitHub authentication failed")

    monkeypatch.setattr("slackbot.search.search_issues", fake_search_issues)

    result = await _read_github_issues_async("is:issue auth", "prefecthq/prefect", 3)

    assert "authentication failed" in result
    assert "temporarily unavailable" in result


@pytest.mark.asyncio
async def test_read_github_issues_returns_rate_limit_message(monkeypatch):
    async def fake_search_issues(*args, **kwargs):
        raise GitHubRateLimitError("GitHub API rate limit exceeded")

    monkeypatch.setattr("slackbot.search.search_issues", fake_search_issues)

    result = await _read_github_issues_async("is:issue rate", "prefecthq/prefect", 3)

    assert "rate limit" in result
    assert "temporarily unavailable" in result
