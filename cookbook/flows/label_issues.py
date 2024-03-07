from enum import Enum

import marvin
from gh_util.functions import add_labels_to_issue, fetch_repo_labels
from gh_util.types import GitHubIssueEvent, GitHubLabel
from prefect import flow, task
from prefect.events.schemas import DeploymentTrigger


@task
async def get_appropriate_labels(
    issue_body: str, label_options: set[GitHubLabel], existing_labels: set[GitHubLabel]
) -> set[str]:
    LabelOption = Enum(
        "LabelOption",
        {label.name: label.name for label in label_options.union(existing_labels)},
    )

    @marvin.fn
    async def get_labels(
        body: str, existing_labels: list[GitHubLabel]
    ) -> set[LabelOption]:  # type: ignore
        """Return appropriate labels for a GitHub issue based on its body.

        If existing labels are sufficient, return them.
        """

    return {i.value for i in await get_labels(issue_body, existing_labels)}


@flow(log_prints=True)
async def label_issues(event_body_json: str):
    """Label issues based on incoming webhook events from GitHub."""
    event = GitHubIssueEvent.model_validate_json(event_body_json)

    print(f"Issue '#{event.issue.number} - {event.issue.title}' was {event.action}")

    owner, repo = event.repository.owner.login, event.repository.name

    label_options = await task(fetch_repo_labels)(owner, repo)

    labels = await get_appropriate_labels(
        issue_body=event.issue.body,
        label_options=label_options,
        existing_labels=set(event.issue.labels),
    )

    await task(add_labels_to_issue)(
        owner=owner,
        repo=repo,
        issue_number=event.issue.number,
        new_labels=labels,
    )

    print(f"Labeled issue with {' | '.join(labels)!r}")


if __name__ == "__main__":
    label_issues.serve(
        name="Label GitHub Issues",
        triggers=[
            DeploymentTrigger(
                expect={"marvin.issue*"},
                parameters={"event_body_json": "{{ event.payload.body }}"},
            )
        ],
    )
