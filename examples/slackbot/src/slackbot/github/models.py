"""GitHub API data models."""

from datetime import datetime

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """GitHub user."""

    login: str | None = None
    id: int | None = None
    avatar_url: str | None = None


class GitHubLabel(BaseModel):
    """GitHub label."""

    name: str = Field(default="")
    color: str = Field(default="")
    description: str | None = Field(default="")


class GitHubComment(BaseModel):
    """GitHub comment."""

    body: str = Field(default="")
    user: GitHubUser = Field(default_factory=GitHubUser)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GitHubIssue(BaseModel):
    """GitHub issue."""

    created_at: datetime = Field(...)
    html_url: str = Field(...)
    number: int = Field(...)
    title: str = Field(default="")
    body: str = Field(default="")
    labels: list[GitHubLabel] = Field(default_factory=list)
    user: GitHubUser = Field(default_factory=GitHubUser)
    state: str = Field(default="open")


class GitHubDiscussion(BaseModel):
    """GitHub discussion."""

    id: str = Field(...)
    number: int = Field(...)
    title: str = Field(default="")
    body: str = Field(default="")
    html_url: str = Field(...)
    created_at: datetime = Field(...)
    category: dict = Field(default_factory=dict)
    author: GitHubUser = Field(default_factory=GitHubUser)
    state: str = Field(default="open")


class DiscussionCategory(BaseModel):
    """GitHub discussion category."""

    id: str = Field(...)
    name: str = Field(...)
    emoji: str = Field(default="")
    description: str = Field(default="")
    is_answerable: bool = Field(default=False)
