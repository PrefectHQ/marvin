"""Loaders for GitHub."""
import asyncio
import fnmatch
import functools
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import httpx
from pydantic import BaseModel, Field, validator

from marvin.loaders.base import Loader
from marvin.models.digests import Digest
from marvin.utilities.logging import read_stream
from marvin.utilities.strings import split_text


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

    html_url: str = Field(...)
    number: int = Field(...)
    title: str = Field(default="")
    body: str | None = Field(default="")
    labels: List[GitHubLabel] = Field(default_factory=GitHubLabel)
    user: GitHubUser = Field(default_factory=GitHubUser)


class GitHubIssueLoader(Loader):
    """Loader for GitHub issues for a given repository."""

    repo: str = Field(...)
    n_issues: int = Field(default=50)
    request_headers: Dict[str, str] = Field(default_factory=dict)

    @validator("request_headers", always=True)
    def auth_headers(cls, v):
        """Add authentication headers if a GitHub token is available."""
        v.update({"Accept": "application/vnd.github.v3+json"})
        if token := os.environ.get("GITHUB_TOKEN"):
            v["Authorization"] = f"Bearer {token}"
        return v

    @staticmethod
    @functools.lru_cache()
    def _get_issue_comments(
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
        while True:
            response = httpx.get(
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

    def _get_issues(self, per_page: int = 100) -> List[GitHubIssue]:
        """
        Get a list of all issues for the given repository.

        Returns:
            A list of `GitHubIssue` objects, each representing an issue.
        """
        url = f"https://api.github.com/repos/{self.repo}/issues"
        issues = []
        page = 1
        while True:
            if len(issues) >= self.n_issues:
                break
            remaining = self.n_issues - len(issues)
            response = httpx.get(
                url=url,
                headers=self.request_headers,
                params={
                    "per_page": remaining if remaining < per_page else per_page,
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

    async def load(self) -> Digest:
        """
        Load all issues for the given repository.

        Returns:
            A list of `Document` objects, each representing an issue.
        """
        digest = Digest()
        for issue in self._get_issues():
            text = f"{issue.title}\n{issue.body}"
            for comment in self._get_issue_comments(
                self.repo, tuple(self.request_headers.items()), issue.number
            ):
                text += f"\n\n{comment.user.login}: {comment.body}\n\n"
            metadata = {
                "source": issue.html_url,
                "title": issue.title,
                "labels": ",".join([label.name for label in issue.labels]),
            }
            digest.ids.append(f"gh_issue/{issue.number}")
            digest.documents.append(text)
            digest.metadatas.append(metadata)
        return digest


class GitHubRepoLoader(Loader):
    """Loader for files on GitHub that match a glob pattern."""

    repo: str = Field(...)
    glob: str = Field(default="*")
    exclude_glob: str | None = Field(default=None)

    @validator("repo")
    def validate_repo(cls, v):
        """Validate the GitHub repository."""
        if "/" not in v:
            raise ValueError(
                "Must provide a GitHub repository in the format 'owner/repo'"
            )
        return f"https://github.com/{v}.git"

    async def load(self) -> Digest:
        """Load files from GitHub that match the glob pattern."""
        tmp_dir = tempfile.mkdtemp()
        try:
            process = await asyncio.create_subprocess_exec(
                *["git", "clone", "--depth", "1", self.repo, tmp_dir],
                stderr=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
            )

            await asyncio.gather(
                read_stream(process.stdout, self.logger.debug),
                read_stream(process.stderr, self.logger.debug),
            )

            if (await process.wait()) != 0:
                raise OSError(
                    f"Failed to clone repository:\n {process.stderr.decode()}"
                )

            # Read the contents of each file that matches the glob pattern
            digest = Digest()
            matched_files = [p for p in Path(tmp_dir).glob(self.glob) if p.is_file()]
            if self.exclude_glob:
                matched_files = [
                    file
                    for file in matched_files
                    if not fnmatch.fnmatch(file, self.exclude_glob)
                ]

            for file in matched_files:
                self.logger.debug(f"Loading file: {file!r}")
                with open(file, "r") as f:
                    text = f.read()

                text_chunks = split_text(text, 1000)
                num_chunks = len(text_chunks)
                metadata = {
                    "source": "/".join(
                        [
                            self.repo.replace(".git", ""),
                            "tree/main",
                            str(file.relative_to(tmp_dir)),
                        ]
                    )
                }
                digest.ids.extend(
                    [f"gh_file/{metadata['source']}/{i}" for i in range(num_chunks)]
                )
                digest.documents.extend(text_chunks)
                digest.metadatas.extend([metadata] * num_chunks)
            return digest
        finally:
            shutil.rmtree(tmp_dir)
