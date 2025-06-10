import os
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

import marvin
from marvin.utilities.logging import get_logger


async def _get_token() -> str:
    try:
        from prefect.blocks.system import Secret

        return (await Secret.aload(name="github-token")).get()
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
    body: str = Field(default="")
    labels: list[GitHubLabel] = Field(default_factory=GitHubLabel)
    user: GitHubUser = Field(default_factory=GitHubUser)
