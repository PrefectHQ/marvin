from enum import Enum
from functools import wraps
from typing import Callable, TypeVar

from devtools import debug
from gh_util.logging import get_logger
from gh_util.types import GitHubIssueEvent, GitHubPullRequestEvent, GitHubWebhookRequest
from pydantic import BaseModel

logger = get_logger("handlers")

M = TypeVar("M", bound=BaseModel)


class EventType(Enum):
    RELEASE = "release"
    PULL_REQUEST = "pull_request"
    PULL_REQUEST_REVIEW_COMMENT = "pull_request_review_comment"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"


def log_id(func: Callable[..., M]) -> Callable[..., M]:
    @wraps(func)
    def wrapper(request: GitHubWebhookRequest, *args, **kwargs) -> M:
        logger.info_kv(
            "WHO?",
            f"{request.event.sender.login} triggered an event: {request.headers.event}",
        )
        return func(request, *args, **kwargs)

    return wrapper


## EVENT HANDLERS


@log_id
async def default_handler(request: GitHubWebhookRequest) -> GitHubWebhookRequest:
    debug(request)
    print(f"Unhandled event: {request.headers.event}")
    return request


@log_id
async def handle_release_event(request: GitHubWebhookRequest) -> M:
    release = request.event.release
    print(f"New release: {release.name} (tag: {release.tag_name})")
    # TODO
    return request


@log_id
async def handle_pr_event(request: GitHubWebhookRequest) -> M:
    event = GitHubPullRequestEvent.model_validate(request.event.model_dump())

    pr = event.pull_request

    if request.headers.event == EventType.PULL_REQUEST.value:
        print(f"New PR: {pr.title} (#{pr.number})")
    elif request.headers.event == EventType.PULL_REQUEST_REVIEW_COMMENT.value:
        comment = request.event.comment
        print(f"New PR comment: {comment.body} (PR #{pr.number})")
    # TODO

    return request


@log_id
async def handle_issue_event(request: GitHubWebhookRequest) -> M:
    event = GitHubIssueEvent.model_validate(request.event.model_dump())

    issue = event.issue

    if event == EventType.ISSUES.value:
        print(f"New issue: {issue.title} (#{issue.number})")

    elif event == EventType.ISSUE_COMMENT.value:
        print(f"New issue comment: {event.comment.body} (Issue #{issue.number})")
    # TODO

    return request


## MAPPINGS

DEFAULT_EVENT_HANDLERS: dict[EventType, Callable[..., M]] = {
    EventType.RELEASE.value: handle_release_event,
    EventType.PULL_REQUEST.value: handle_pr_event,
    EventType.PULL_REQUEST_REVIEW_COMMENT.value: handle_pr_event,
    EventType.ISSUES.value: handle_issue_event,
    EventType.ISSUE_COMMENT.value: handle_issue_event,
}

REPO_EVENT_HANDLERS: dict[str, dict[EventType, Callable]] = {
    "zzstoatzz/gh": DEFAULT_EVENT_HANDLERS,
    "zzstoatzz/raggy": DEFAULT_EVENT_HANDLERS,
}
