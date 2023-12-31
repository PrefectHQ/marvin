import os
from datetime import datetime
from typing import List, Optional

import httpx
from pydantic import BaseModel, Field, field_validator

import marvin
from marvin.utilities.logging import get_logger
from marvin.utilities.strings import slice_tokens


async def get_token() -> str:
    try:
        from prefect.blocks.system import Secret

        return (await Secret.load(name="github-token")).get()  # type: ignore
    except (ImportError, ValueError) as exc:
        getattr(get_logger("marvin"), "debug_kv")(
            (
                "Prefect Secret for GitHub token not retrieved. "
                f"{exc.__class__.__name__}: {exc}"
                "red"
            ),
        )

    try:
        return getattr(marvin.settings, "github_token")
    except AttributeError:
        pass

    if token := os.environ.get("MARVIN_GITHUB_TOKEN", ""):
        return token

    raise RuntimeError("GitHub token not found")


class GitHubUser(BaseModel):
    """GitHub user."""

    login: Optional[str] = None


class GitHubComment(BaseModel):
    """GitHub comment."""

    body: str = Field(default="")
    user: GitHubUser = Field(default_factory=GitHubUser)


class GitHubLabel(BaseModel):
    """GitHub label."""

    name: str = Field(default="")


class GitHubIssue(BaseModel):
    """GitHub issue."""

    created_at: datetime = Field(...)
    html_url: str = Field(...)
    number: int = Field(...)
    title: str = Field(default="")
    body: Optional[str] = Field(default="")
    labels: List[GitHubLabel] = Field(default_factory=GitHubLabel)
    user: GitHubUser = Field(default_factory=GitHubUser)

    @field_validator("body")
    def validate_body(cls, v: str) -> str:
        if not v:
            return ""
        return v


async def search_github_issues(
    query: str, repo: str = "prefecthq/prefect", n: int = 3
) -> str:
    """
    Use the GitHub API to search for issues in a given repository. Do
    not alter the default value for `n` unless specifically requested by
    a user.

    For example, to search for open issues about AttributeErrors with the
    label "bug" in PrefectHQ/prefect:
        - repo: prefecthq/prefect
        - query: label:bug is:open AttributeError
    """
    headers = {"Accept": "application/vnd.github.v3+json"}

    headers["Authorization"] = f"Bearer {await get_token()}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/search/issues",
            headers=headers,
            params={
                "q": query if "repo:" in query else f"repo:{repo} {query}",
                "order": "desc",
                "per_page": n,
            },
        )
        response.raise_for_status()

    issues_data = response.json()["items"]

    # enforce 1000 token limit per body
    for issue in issues_data:
        if not issue["body"]:
            continue
        issue["body"] = slice_tokens(issue["body"], 1000)

    issues = [GitHubIssue(**issue) for issue in issues_data]

    summary = "\n\n".join(
        f"{issue.title} ({issue.html_url}):\n{issue.body}" for issue in issues
    )
    if not summary.strip():
        return "No issues found."
    return summary
