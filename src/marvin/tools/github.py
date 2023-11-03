from datetime import datetime
from typing import List, Optional

import httpx
from pydantic import BaseModel, Field, validator

import marvin
from marvin.tools import Tool
from marvin.utilities.strings import slice_tokens


class GitHubUser(BaseModel):
    """GitHub user."""

    login: str


class GitHubComment(BaseModel):
    """GitHub comment."""

    body: str = Field(default_factory=str)
    user: GitHubUser = Field(default_factory=GitHubUser)


class GitHubLabel(BaseModel):
    """GitHub label."""

    name: str = Field(default_factory=str)


class GitHubIssue(BaseModel):
    """GitHub issue."""

    created_at: datetime = Field(...)
    html_url: str = Field(...)
    number: int = Field(...)
    title: str = Field(default_factory=str)
    body: Optional[str] = Field(default_factory=str)
    labels: List[GitHubLabel] = Field(default_factory=GitHubLabel)
    user: GitHubUser = Field(default_factory=GitHubUser)

    @validator("body", always=True)
    def validate_body(cls, v):
        if not v:
            return ""
        return v


class GitHubCodeResult(BaseModel):
    name: str
    path: str
    html_url: str
    repository: dict
    fragment: str = Field(default_factory=str)


async def search_github_issues(
    query: str, repo: str = "prefecthq/prefect", n: int = 3, max_tokens: int = 1000
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

    if token := marvin.settings.github_token:
        headers["Authorization"] = f"Bearer {token.get_secret_value()}"

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
        issue["body"] = slice_tokens(issue["body"], max_tokens)

    issues = [GitHubIssue(**issue) for issue in issues_data]

    summary = "\n\n".join(
        f"{issue.title} ({issue.html_url}):\n{issue.body}" for issue in issues
    )
    if not summary.strip():
        raise ValueError("No issues found.")
    return summary


class SearchGitHubIssues(Tool):
    """Tool for searching GitHub issues."""

    description: str = "Use the GitHub API to search for issues in a given repository."

    async def run(self, query: str, repo: str = "prefecthq/prefect", n: int = 3) -> str:
        """
        Use the GitHub API to search for issues in a given repository. Do
        not alter the default value for `n` unless specifically requested by
        a user.

        For example, to search for open issues about AttributeErrors with the
        label "bug" in PrefectHQ/prefect:
            - repo: prefecthq/prefect
            - query: label:bug is:open AttributeError
        """
        return await search_github_issues(query=query, repo=repo, n=n)


async def search_github_repo(
    query: str, repo: str = "prefecthq/prefect", n: int = 3, max_tokens: str = 1000
) -> str:
    headers = {"Accept": "application/vnd.github.v3.text-match+json"}

    if token := marvin.settings.github_token:
        headers["Authorization"] = f"Bearer {token.get_secret_value()}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/search/code",
            headers=headers,
            params={"q": f"{query} repo:{repo}", "per_page": n},
        )
        response.raise_for_status()

    code_data = response.json().get("items", [])
    code_results = [
        GitHubCodeResult(
            name=item["name"],
            path=item["path"],
            html_url=item["html_url"],
            repository=item["repository"],
            fragment="\n".join(
                match.get("fragment")
                for match in item.get("text_matches", [])
                if match["property"] == "content"
            ),
        )
        for item in code_data
    ]

    return (
        "\n\n".join(
            f"{code.name} ({code.html_url}):\n{slice_tokens(code.fragment, max_tokens)}"
            for code in code_results
        )
        if code_data
        else "No code found."
    )
