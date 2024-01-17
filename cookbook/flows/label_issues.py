from typing import Iterable

import marvin
from gh_util.functions import add_labels_to_issue, fetch_repo_labels
from gh_util.types import GitHubIssueEvent, GitHubLabel
from prefect import flow, task


@task
def classify_issue(issue_body: str, labels: Iterable[GitHubLabel]):
    """Classify an issue based on its body"""
    return marvin.classify(issue_body, labels=[label.name for label in labels])


# want to do {{ event.payload.body | from_json }} -> GitHubIssueEvent directly
@flow(log_prints=True)
async def label_issues(event_body_str: str):
    """Label issues based on their action"""
    issue_event = GitHubIssueEvent.model_validate_json(event_body_str)
    print(
        f"Issue '#{issue_event.issue.number} - {issue_event.issue.title}' was {issue_event.action}"
    )

    issue_body = issue_event.issue.body

    owner, repo = issue_event.repository.owner.login, issue_event.repository.name

    repo_labels = await fetch_repo_labels(owner, repo)

    label = classify_issue(issue_body, repo_labels)

    await add_labels_to_issue(owner, repo, issue_event.issue.number, {label})

    print(f"Labeled issue with '{label}'")
