"""Core GitHub API client."""

import os
from typing import Any

import httpx
from prefect.blocks.system import Secret

import marvin
from marvin.utilities.logging import get_logger

from ..settings import settings
from .exceptions import (
    GitHubAuthError,
    GitHubError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)


class GitHubClient:
    """Centralized GitHub API client with consistent auth and error handling."""

    def __init__(self, token: str | None = None):
        self.token = token
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GitHubClient":
        """Async context manager entry."""
        if not self.token:
            self.token = await self._get_token()

        self._client = httpx.AsyncClient(headers=self._get_headers(), timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_headers(self) -> dict[str, str]:
        """Get standard GitHub API headers."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _get_token(self) -> str:
        """Get GitHub token from various sources."""
        # Try Prefect Secret first (for slackbot)
        try:
            secret = await Secret.aload(name=settings.github_token_secret_name)
            return secret.get()
        except (ImportError, ValueError, AttributeError) as exc:
            logger = get_logger("slackbot.github")
            logger.debug(f"Prefect Secret not available: {exc}")

        # Fallback to Marvin settings
        try:
            return getattr(marvin.settings, "github_token")
        except AttributeError:
            pass

        # Fallback to environment variable
        if token := os.environ.get("MARVIN_GITHUB_TOKEN", ""):
            return token

        raise GitHubAuthError("GitHub token not found in any source")

    def _handle_response_errors(self, response: httpx.Response) -> None:
        """Handle common GitHub API errors."""
        if response.status_code == 401:
            raise GitHubAuthError("GitHub authentication failed")
        elif response.status_code == 403:
            if "rate limit" in response.text.lower():
                raise GitHubRateLimitError("GitHub API rate limit exceeded")
            else:
                raise GitHubAuthError("GitHub access forbidden")
        elif response.status_code == 404:
            raise GitHubNotFoundError("GitHub resource not found")
        elif response.status_code >= 400:
            raise GitHubError(
                f"GitHub API error {response.status_code}: {response.text}"
            )

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make GET request with error handling."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        response = await self._client.get(url, **kwargs)
        self._handle_response_errors(response)
        return response

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make POST request with error handling."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        response = await self._client.post(url, **kwargs)
        self._handle_response_errors(response)
        return response

    async def graphql(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute GraphQL query."""
        response = await self.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables or {}},
        )

        data = response.json()
        if "errors" in data:
            raise GitHubError(f"GraphQL errors: {data['errors']}")

        return data["data"]
