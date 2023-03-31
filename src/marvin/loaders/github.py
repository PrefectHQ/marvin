"""Loaders for GitHub."""
import asyncio
import functools
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiofiles
import chardet
import httpx
import pendulum
from pydantic import BaseModel, Field, validator

import marvin
from marvin.loaders.base import Loader
from marvin.models.documents import Document
from marvin.models.metadata import Metadata
from marvin.utilities.collections import multi_glob
from marvin.utilities.strings import rm_html_comments, rm_text_after


async def read_file_with_chardet(file_path, errors="replace"):
    async with aiofiles.open(file_path, "rb") as f:
        content = await f.read()
        encoding = chardet.detect(content)["encoding"]

    async with aiofiles.open(file_path, "r", encoding=encoding, errors=errors) as f:
        text = await f.read()
    return text


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

    created_at: pendulum.DateTime = Field(...)
    html_url: str = Field(...)
    number: int = Field(...)
    title: str = Field(default="")
    body: Optional[str] = Field(default="")
    labels: List[GitHubLabel] = Field(default_factory=GitHubLabel)
    user: GitHubUser = Field(default_factory=GitHubUser)

    @validator("body", always=True)
    def validate_body(cls, v):
        if not v:
            return ""
        return v


class GitHubIssueLoader(Loader):
    """Loader for GitHub issues in a given repository.

    **Beware** the [GitHub API rate limit](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting).

    Use `use_GH_token` to authenticate with your `GITHUB_TOKEN` environment variable and increase the rate limit.

    """  # noqa: E501

    source_type: str = "github issue"

    repo: str = Field(...)
    n_issues: int = Field(default=50)

    include_comments: bool = Field(default=False)
    ignore_body_after: str = Field(default="### Checklist")
    ignore_users: List[str] = Field(default_factory=list)
    use_GH_token: bool = Field(default=False)

    request_headers: Dict[str, str] = Field(default_factory=dict)

    @validator("request_headers", always=True)
    def auth_headers(cls, v, values):
        """Add authentication headers if a GitHub token is available."""
        v.update({"Accept": "application/vnd.github.v3+json"})
        if values["use_GH_token"] and (
            token := marvin.settings.GITHUB_TOKEN.get_secret_value()
        ):
            v["Authorization"] = f"Bearer {token}"
        return v

    @staticmethod
    @functools.lru_cache(maxsize=2048)
    async def _get_issue_comments(
        repo: str,
        request_header_items: Tuple[Tuple[str, str]],
        issue_number: int,
        per_page: int = 100,
    ) -> List[GitHubComment]:
        """
        Get a list of all comments for the given issue.

        Returns:
            A list of dictionaries, each representing a comment.
        """
        url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
        comments = []
        page = 1
        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    url=url,
                    headers=dict(request_header_items),
                    params={"per_page": per_page, "page": page},
                )
                response.raise_for_status()
                if not (new_comments := response.json()):
                    break
                comments.extend([GitHubComment(**comment) for comment in new_comments])
                page += 1
            return comments

    async def _get_issues(self, per_page: int = 100) -> List[GitHubIssue]:
        """
        Get a list of all issues for the given repository.

        per_page: The number of issues to request per page.

        Returns:
            A list of `GitHubIssue` objects, each representing an issue.
        """  # noqa: E501
        url = f"https://api.github.com/repos/{self.repo}/issues"
        issues = []
        page = 1
        async with httpx.AsyncClient() as client:
            while len(issues) < self.n_issues:
                remaining = self.n_issues - len(issues)
                response = await client.get(
                    url=url,
                    headers=self.request_headers,
                    params={
                        "per_page": min(remaining, per_page),
                        "page": page,
                        "include": "comments",
                    },
                )
                response.raise_for_status()
                if not (new_issues := response.json()):
                    break
                issues.extend([GitHubIssue(**issue) for issue in new_issues])
                page += 1
            return issues

    async def load(self) -> list[Document]:
        """
        Load all issues for the given repository.

        Returns:
            A list of `Document` objects, each representing an issue.
        """
        documents = []
        for issue in await self._get_issues():
            self.logger.debug(f"Found {issue.title!r}")
            clean_issue_body = rm_text_after(
                rm_html_comments(issue.body), self.ignore_body_after
            )
            text = f"\n\n##**{issue.title}:**\n{clean_issue_body}\n"
            if self.include_comments:
                for (
                    comment
                ) in await self._get_issue_comments(  # hashable headers for lru_cache
                    self.repo, tuple(self.request_headers.items()), issue.number
                ):
                    if comment.user.login not in self.ignore_users:
                        text += f"**[{comment.user.login}]**: {comment.body}\n\n"
            metadata = Metadata(
                source=self.source_type,
                link=issue.html_url,
                title=issue.title,
                labels=", ".join([label.name for label in issue.labels]),
                created_at=issue.created_at.timestamp(),
            )
            documents.extend(
                await Document(
                    text=text,
                    metadata=metadata,
                ).to_excerpts()
            )
        return documents


class GitHubRepoLoader(Loader):
    """Loader for files on GitHub that match a glob pattern."""

    source_type: str = "github source code"

    repo: str = Field(...)
    include_globs: list[str] = Field(default=None)
    exclude_globs: list[str] = Field(default=None)

    @validator("repo")
    def validate_repo(cls, v):
        """Validate the GitHub repository."""
        if not re.match(r"^[^/\s]+/[^/\s]+$", v):
            raise ValueError(
                "Must provide a GitHub repository in the format 'owner/repo'"
            )
        return f"https://github.com/{v}.git"

    async def load(self) -> list[Document]:
        """Load files from GitHub that match the glob pattern."""
        async with aiofiles.tempfile.TemporaryDirectory(suffix="marvin") as tmp_dir:
            process = await asyncio.create_subprocess_exec(
                *["git", "clone", "--depth", "1", self.repo, tmp_dir],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            if (await process.wait()) != 0:
                raise OSError(
                    f"Failed to clone repository:\n {await process.stderr.read()}"
                )

            self.logger.debug(f"{await process.stdout.read()}")

            # Read the contents of each file that matches the glob pattern
            documents = []

            for file in multi_glob(tmp_dir, self.include_globs, self.exclude_globs):
                self.logger.debug(f"Loading file: {file!r}")

                metadata = Metadata(
                    source=self.source_type,
                    link="/".join(
                        [
                            self.repo.replace(".git", ""),
                            "tree/main",
                            str(file),
                        ]
                    ),
                    title=file.name,
                    filename=file.name,
                )
                documents.extend(
                    await Document(
                        text=await read_file_with_chardet(Path(tmp_dir) / file),
                        metadata=metadata,
                    ).to_excerpts()
                )
            return documents
