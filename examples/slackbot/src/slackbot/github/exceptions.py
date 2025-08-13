"""GitHub API exceptions."""


class GitHubError(Exception):
    """Base exception for GitHub API errors."""

    pass


class GitHubAuthError(GitHubError):
    """GitHub authentication error."""

    pass


class GitHubNotFoundError(GitHubError):
    """GitHub resource not found error."""

    pass


class GitHubRateLimitError(GitHubError):
    """GitHub rate limit exceeded error."""

    pass
