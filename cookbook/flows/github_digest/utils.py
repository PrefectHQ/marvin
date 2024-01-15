from datetime import datetime

import httpx
import marvin


async def fetch_contributor_data(
    owner: str,
    repo: str,
    since: datetime,
    max: int = 100,
    excluded_users: set[str] | None = None,
    token: str | None = None,
) -> dict[str, dict[str, str | list]]:
    if not excluded_users:
        excluded_users = {}

    if not token:
        token = marvin.settings.github_token.get_secret_value()

    events_url = f"https://api.github.com/repos/{owner}/{repo}/events?per_page={max}"

    contributors_activity = {}

    async with httpx.AsyncClient(
        headers={
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token}",
        }
    ) as client:
        events = (await client.get(events_url)).json()

        for event in events:
            if (actor := event.get("actor")) and actor["login"] in excluded_users:
                continue
            created_at = datetime.fromisoformat(event["created_at"].rstrip("Z"))
            if created_at < since:
                continue

            contributor_username = actor["login"] if actor else "unknown"

            if contributor_username not in contributors_activity:
                contributors_activity[contributor_username] = {
                    "created_issues": [],
                    "created_pull_requests": [],
                    "merged_commits": [],
                }

            if (
                event["type"] == "IssuesEvent"
                and event["payload"]["action"] == "opened"
            ):
                contributors_activity[contributor_username]["created_issues"].append(
                    event["payload"]["issue"]
                )

            elif (
                event["type"] == "PullRequestEvent"
                and event["payload"]["action"] == "opened"
            ):
                contributors_activity[contributor_username][
                    "created_pull_requests"
                ].append(event["payload"]["pull_request"])

            elif event["type"] == "PushEvent":
                for commit_data in event["payload"]["commits"]:
                    commit = (await client.get(commit_data["url"])).json()
                    commit_message = commit["commit"]["message"].split("\n")
                    cleaned_commit_message = "\n".join(
                        line
                        for line in commit_message
                        if not line.strip().lower().startswith("co-authored-by:")
                    )
                    commit_msg = commit["commit"]["message"] = cleaned_commit_message

                    if (
                        "Merge remote-tracking branch" not in commit_msg
                        and "Merge branch" not in commit_msg
                    ):
                        contributors_activity[contributor_username][
                            "merged_commits"
                        ].append(commit)

    return contributors_activity


async def cluster_issues():
    pass
