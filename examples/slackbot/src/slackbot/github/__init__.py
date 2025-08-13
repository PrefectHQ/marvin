"""GitHub API integration module."""

from .client import GitHubClient
from .models import (
    GitHubUser,
    GitHubLabel,
    GitHubComment,
    GitHubIssue,
    GitHubDiscussion,
    DiscussionCategory,
)
from .issues import search_issues, format_issues_summary
from .discussions import (
    search_discussions,
    get_discussion_categories,
    create_discussion,
    create_discussion_from_thread,
    format_discussions_summary,
)
from .exceptions import (
    GitHubError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)

__all__ = [
    # Client
    "GitHubClient",
    # Models
    "GitHubUser",
    "GitHubLabel",
    "GitHubComment",
    "GitHubIssue",
    "GitHubDiscussion",
    "DiscussionCategory",
    # Issues
    "search_issues",
    "format_issues_summary",
    # Discussions
    "search_discussions",
    "get_discussion_categories",
    "create_discussion",
    "create_discussion_from_thread",
    "format_discussions_summary",
    # Exceptions
    "GitHubError",
    "GitHubAuthError",
    "GitHubNotFoundError",
    "GitHubRateLimitError",
]
