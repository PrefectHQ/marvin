"""GitHub Issues operations."""

from ..strings import slice_tokens
from .client import GitHubClient
from .models import GitHubIssue


async def search_issues(
    query: str,
    repo: str = "prefecthq/prefect",
    n: int = 3,
    client: GitHubClient | None = None,
) -> list[GitHubIssue]:
    """
    Search for GitHub issues in a repository.

    Args:
        query: Search query string
        repo: Repository in format 'owner/repo'
        n: Number of issues to return
        client: Optional GitHub client (will create one if not provided)

    Returns:
        List of GitHub issues
    """
    should_close = client is None
    if client is None:
        client = GitHubClient()

    try:
        if should_close:
            await client.__aenter__()

        # Add repo to query if not already present
        search_query = query if "repo:" in query else f"repo:{repo} {query}"

        response = await client.get(
            "https://api.github.com/search/issues",
            params={
                "q": search_query,
                "order": "desc",
                "per_page": n,
            },
        )

        issues_data = response.json()["items"]

        # Truncate long issue bodies
        TOKEN_LIMIT = 1500
        for issue in issues_data:
            if issue.get("body"):
                issue["body"] = slice_tokens(issue["body"], TOKEN_LIMIT)

        return [GitHubIssue(**issue) for issue in issues_data]

    finally:
        if should_close:
            await client.__aexit__(None, None, None)


async def format_issues_summary(issues: list[GitHubIssue]) -> str:
    """Format issues into a readable summary."""
    if not issues:
        return "No issues found."

    return "\n\n".join(
        f"{issue.title} ({issue.html_url}):\n{issue.body}" for issue in issues
    )
