from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class GitHubUser(BaseModel):
    """GitHub user."""

    login: str


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

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually. # noqa
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information. # noqa
    @validator("body", always=True)
    def validate_body(cls, v):
        if not v:
            return ""
        return v
