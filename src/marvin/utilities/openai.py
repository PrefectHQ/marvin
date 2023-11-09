import openai


def get_client(_async: bool = True, **kwargs):
    from marvin import settings

    client_cls = getattr(openai, "AsyncClient" if _async else "Client")

    return client_cls(
        api_key=settings.openai.api_key.get_secret_value(),
        organization=settings.openai.organization,
        **kwargs,
    )
