import httpx

import marvin
from marvin.loaders.github import GitHubIssue
from marvin.plugins import plugin
from marvin.utilities.strings import slice_tokens


@plugin
async def search_github_issues(
    query: str, repo: str = "prefecthq/prefect", n: int = 3
) -> str:
    """
    Use the GitHub API to search for issues in a given repository.
    """

    url = "https://api.github.com/search/issues"

    headers = {"Accept": "application/vnd.github.v3+json"}

    if token := marvin.settings.GITHUB_TOKEN.get_secret_value():
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            params={
                "q": f"repo:{repo} {query}",
                "order": "desc",
                "per_page": n,
            },
        )
        response.raise_for_status()

    issues_data = response.json()["items"]

    # enforce 1000 token limit per body
    for issue in issues_data:
        issue["body"] = slice_tokens(issue["body"], 1000)

    issues = [GitHubIssue(**issue) for issue in issues_data]

    return "\n\n".join(
        f"{issue.title} ({issue.html_url}):\n{issue.body}" for issue in issues
    )
