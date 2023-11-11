from functools import cache
from typing import Optional

from openai import AsyncClient


def get_client() -> AsyncClient:
    from marvin import settings

    api_key: Optional[str] = (
        settings.openai.api_key.get_secret_value() if settings.openai.api_key else None
    )
    organization: Optional[str] = settings.openai.organization
    return _get_client_memoized(api_key=api_key, organization=organization)


@cache
def _get_client_memoized(
    api_key: Optional[str],
    organization: Optional[str],
) -> AsyncClient:
    """
    This function is memoized to ensure that only one instance of the client is
    created for a given api key / organization pair.
    """
    return AsyncClient(
        api_key=api_key,
        organization=organization,
    )
