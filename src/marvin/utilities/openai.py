"""Module for working with OpenAI."""

import asyncio
from functools import lru_cache
from typing import Optional

from openai import AsyncClient


def get_openai_client() -> AsyncClient:
    """
    Retrieves an OpenAI client with the given api key and organization.

    Returns:
        The OpenAI client with the given api key and organization.

    Example:
        Retrieving an OpenAI client
        ```python
        from marvin.utilities.openai import get_client

        client = get_client()
        ```
    """
    from marvin import settings

    api_key: Optional[str] = (
        settings.openai.api_key.get_secret_value() if settings.openai.api_key else None
    )
    organization: Optional[str] = settings.openai.organization
    return _get_client_memoized(
        api_key=api_key, organization=organization, loop=asyncio.get_event_loop()
    )


@lru_cache
def _get_client_memoized(
    api_key: Optional[str],
    organization: Optional[str],
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> AsyncClient:
    """
    This function is memoized to ensure that only one instance of the client is
    created for a given api key / organization / loop tuple.

    The `loop` is an important key to ensure that the client is not re-used
    across multiple event loops (which can happen when using the `run_sync`
    function). Attempting to re-use the client across multiple event loops
    can result in a `RuntimeError: Event loop is closed` error or infinite hangs.
    """
    return AsyncClient(
        api_key=api_key,
        organization=organization,
    )
