from typing import Optional

from openai import AsyncClient


def get_client() -> AsyncClient:
    from marvin import settings

    api_key: Optional[str] = (
        settings.openai.api_key.get_secret_value() if settings.openai.api_key else None
    )
    organization: Optional[str] = settings.openai.organization

    return AsyncClient(
        api_key=api_key,
        organization=organization,
    )
