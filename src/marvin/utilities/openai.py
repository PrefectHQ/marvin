from openai import AsyncClient


def get_client():
    from marvin import settings

    return AsyncClient(
        api_key=settings.openai.api_key.get_secret_value(),
        organization=settings.openai.organization,
    )
