import inspect
from datetime import date, datetime, timedelta

import httpx
import marvin
from marvin import fn
from marvin.utilities.strings import jinja_env
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
from prefect.blocks.system import Secret

DAILY_DIGEST_TEMPLATE = jinja_env.from_string(
    inspect.cleandoc(
        """
        # GitHub Digest: {{ today }}
        
        Hi {{ username }}! Here's what you've been up to on GitHub today:
        
        ## you created {{ created_issues|length }} issue(s) and opened {{ created_pull_requests|length }} PR(s):
        ### issues
        {% for issue in created_issues %}
        - [{{ issue.title }}]({{ issue.html_url }})
        {% endfor %}
        
        ### PRs
        {% for pr in created_pull_requests %}
        - [{{ pr.title }}]({{ pr.html_url }})
        {% endfor %}
        
        ## you closed {{ closed_issues|length }} issue(s) and merged {{ closed_pull_requests|length }} PR(s):
        ### issues
        {% for issue in closed_issues %}
        - [{{ issue.title }}]({{ issue.html_url }})
        {% endfor %}

        ### PRs
        {% for pr in closed_pull_requests %}
        - [{{ pr.title }}]({{ pr.html_url }})
        {% endfor %}

        ## you committed to {{ committed_repos|length }} repo(s):
        {% for repo in committed_repos %}
        - {{ repo.commits|length }} commits to [{{ repo.name }}](github.com/{{ repo.name }})
        {% endfor %}
        """
    )
)  # noqa: E501


@fn
async def summarize_digest(markdown_digest: str) -> str:
    """Produce a short story based on the GitHub digest.

    The subject of the story is the username greeted in the beginning of the digest.
    """


@task
async def get_digest_data(username, gh_token_secret_name, since, max=100):
    events_url = f"https://api.github.com/users/{username}/events/public?per_page={max}"

    token = await Secret.load(gh_token_secret_name)

    created_issues = []
    created_pull_requests = []
    closed_issues = []
    closed_pull_requests = []
    committed_repos = {}

    async with httpx.AsyncClient(
        headers={
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token.get()}",
        }
    ) as client:
        for event in (await client.get(events_url)).json():
            created_at = datetime.fromisoformat(event["created_at"].rstrip("Z"))
            if created_at < since:
                continue

            if event["type"] == "IssuesEvent":
                issue = event["payload"]["issue"]
                if event["payload"]["action"] == "opened":
                    created_issues.append(issue)
                elif event["payload"]["action"] == "closed":
                    closed_issues.append(issue)

            elif event["type"] == "PullRequestEvent":
                pr = event["payload"]["pull_request"]
                if event["payload"]["action"] == "opened":
                    created_pull_requests.append(pr)
                elif event["payload"]["action"] == "closed":
                    closed_pull_requests.append(pr)

            elif event["type"] == "PushEvent":
                repo_name = event["repo"]["name"]
                commits = event["payload"]["commits"]
                if repo_name not in committed_repos:
                    committed_repos[repo_name] = {
                        "name": repo_name,
                        "commits": [],
                    }
                for commit_data in commits:
                    commit = (await client.get(commit_data["url"])).json()
                    if (
                        "Merge remote-tracking branch"
                        not in commit["commit"]["message"]
                    ):
                        committed_repos[repo_name]["commits"].append(commit)

    digest_data = {
        "today": date.today().strftime("%Y-%m-%d"),
        "created_issues": created_issues,
        "created_pull_requests": created_pull_requests,
        "closed_issues": closed_issues,
        "closed_pull_requests": closed_pull_requests,
        "committed_repos": list(committed_repos.values()),
    }

    return digest_data


@flow
async def daily_github_digest(username: str, gh_token_secret_name: str):
    """
    A flow that creates a daily digest of GitHub activity.

    Args:
        username: The GitHub username to create a digest for.
        gh_token_secret_name: The name of the secret containing a GitHub token.
    """
    since = datetime.utcnow() - timedelta(days=1)

    data = await get_digest_data(username, gh_token_secret_name, since)

    markdown_digest = DAILY_DIGEST_TEMPLATE.render(username=username, **data)

    tldr = await summarize_digest(markdown_digest)

    await create_markdown_artifact(
        key="github-digest",
        markdown=markdown_digest,
        description=tldr,
    )


if __name__ == "__main__":
    import asyncio

    marvin.settings.openai.chat.completions.model = "gpt-4"

    asyncio.run(
        daily_github_digest(username="zzstoatzz", gh_token_secret_name="github-token")
    )
