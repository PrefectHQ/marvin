import httpx

import marvin
from marvin.tools import Tool
from marvin.utilities.models.github import GitHubIssue
from marvin.utilities.strings import slice_tokens


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
        headers = {"Accept": "application/vnd.github.v3+json"}

        if token := marvin.settings.github_token.get_secret_value():
            headers["Authorization"] = f"Bearer {token}"

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
