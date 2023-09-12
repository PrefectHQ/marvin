"""
This module provides tools for interacting with GitHub's API. It includes classes for
representing GitHub users, comments, labels, and issues, as well as a tool for searching
GitHub issues. Each class is rigorously type hinted and documented to attract potential
OSS contributors.
"""
from datetime import datetime
from typing import List, Optional

import httpx
from pydantic import BaseModel, Field

import marvin
from marvin._compat import field_validator
from marvin.tools import Tool
from marvin.utilities.strings import slice_tokens


class GitHubUser(BaseModel):
    """
    Represents a GitHub user.
    """

    login: str = Field(..., description="The login name of the GitHub user")


class GitHubComment(BaseModel):
    """
    Represents a GitHub comment.
    """

    body: str = Field(default="", description="The body text of the comment")
    user: GitHubUser = Field(
        default_factory=lambda: GitHubUser(login=""),
        description="The user who made the comment",
    )


class GitHubLabel(BaseModel):
    """
    Represents a GitHub label.
    """

    name: str = Field(default="", description="The name of the label")


class GitHubIssue(BaseModel):
    """
    Represents a GitHub issue.
    """

    created_at: datetime = Field(
        ..., description="The creation date and time of the issue"
    )
    html_url: str = Field(..., description="The URL of the issue")
    number: int = Field(..., description="The number of the issue")
    title: str = Field(default="", description="The title of the issue")
    body: Optional[str] = Field(default="", description="The body text of the issue")
    labels: List[GitHubLabel] = Field(
        default_factory=list, description="The labels attached to the issue"
    )
    user: GitHubUser = Field(
        default_factory=lambda: GitHubUser(login=""),
        description="The user who created the issue",
    )

    @field_validator("body")
    def validate_body(cls, v: Optional[str]) -> str:
        """
        Validates the body of the issue. If the body is None, it returns an empty string
        """
        return "" if not v else v


class SearchGitHubIssues(Tool):
    """
    Tool for searching GitHub issues.
    """

    description: str = Field(
        ...,
        description="Use the GitHub API to search for issues in a given repository.",
    )

    async def run(self, query: str, repo: str = "prefecthq/prefect", n: int = 3) -> str:  # type: ignore # noqa: E501
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
            issue["body"] = slice_tokens(issue["body"], 1000)

        issues = [GitHubIssue(**issue) for issue in issues_data]

        summary = "\n\n".join(
            f"{issue.title} ({issue.html_url}):\n{issue.body}" for issue in issues
        )
        if not summary.strip():
            raise ValueError("No issues found.")
        return summary
