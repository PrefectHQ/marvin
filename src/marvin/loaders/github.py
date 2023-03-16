"""Loaders for GitHub."""
import asyncio
import fnmatch
import httpx
import os
import shutil
import tempfile
import textwrap
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List

from marvin.models.digests import Digest

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

class GithubIssueLoader:
    """Loader for GitHub issues for a given repository."""

    def __init__(self, repo: str, n_issues: int):
        """
        Initialize the loader with the given repository.

        Args:
            repo: The name of the repository, in the format "<owner>/<repo>"
        """
        self.repo = repo
        self.n_issues = n_issues
        self.request_headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        # If a GitHub token is available, use it to increase the rate limit
        if token := os.environ.get("GITHUB_TOKEN"):
            self.request_headers["Authorization"] = f"Bearer {token}"

    def _get_issue_comments(
        self, issue_number: int, per_page: int = 100
    ) -> List[GitHubComment]:
        """
        Get a list of all comments for the given issue.

        Returns:
            A list of dictionaries, each representing a comment.
        """
        url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}/comments"
        comments = []
        page = 1
        while True:
            response = httpx.get(
                url=url,
                headers=self.request_headers,
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

    def load(self) -> Digest:
        """
        Load all issues for the given repository.

        Returns:
            A list of `Document` objects, each representing an issue.
        """
        digest = Digest()
        issues = self._get_issues()
        for issue in issues:
            text = f"{issue.title}\n{issue.body}"
            for comment in self._get_issue_comments(issue.number):
                text += f"\n\n{comment.user.login}: {comment.body}\n\n"
            metadata = {
                "source": issue.html_url,
                "title": issue.title,
                "labels": ",".join([label.name for label in issue.labels]),
            }
            digest.ids.append(f"{self.repo}#{issue.number}")
            digest.documents.append(text)
            digest.metadatas.append(metadata)
        return digest


class GitHubRepoLoader:
    """Loader for files on GitHub that match a glob pattern."""

    def __init__(self, repo: str, glob: str, exclude_glob: str | None = None):
        """Initialize with the GitHub repository and glob pattern.

        Attrs:
            repo: The organization and repository name, e.g. "prefecthq/prefect"
            glob: The glob pattern to match files, e.g. "**/*.md"
            exclude_glob: A glob pattern to exclude files, e.g. "**/docs/api-ref/**"

        """
        self.repo = f"https://github.com/{repo}.git"
        self.glob = glob
        self.exclude_glob = exclude_glob

    def _split_text_into_chunks(self, text: str, max_tokens: int) -> List[str]:
        return textwrap.wrap(" ".join(text.split()), max_tokens)


    async def load(self) -> Digest:
        """Load files from GitHub that match the glob pattern."""
        tmp_dir = tempfile.mkdtemp()
        try:
            process = await asyncio.create_subprocess_exec(
                *["git", "clone", "--depth", "1", self.repo, tmp_dir]
            )
            if (await process.wait()) != 0:
                raise OSError(
                    f"Failed to clone repository:\n {process.stderr.decode()}"
                )

            # Read the contents of each file that matches the glob pattern
            digest = Digest()
            matched_files = list(Path(tmp_dir).glob(self.glob))
            if self.exclude_glob:
                matched_files = [
                    file
                    for file in matched_files
                    if not fnmatch.fnmatch(file, self.exclude_glob)
                ]
            
            for file in matched_files:
                with open(file, "r") as f:
                    text = f.read()

                metadata_base = {
                    "source": "/".join([self.repo.replace(".git", ""), "tree/main", str(file.relative_to(tmp_dir))])
                }

                text_chunks = self._split_text_into_chunks(text, 4096)
                for index, chunk in enumerate(text_chunks):
                    metadata = metadata_base.copy()
                    metadata["id"] = f"{metadata['source']}#{index}"
                    digest.ids.append(metadata["id"])
                    digest.documents.append(chunk)
                    digest.metadatas.append(metadata)
            return digest
        finally:
            shutil.rmtree(tmp_dir)
            
    async def load_and_store(self, topic_name: str) -> None:
        # topic_name --> collection name
        pass