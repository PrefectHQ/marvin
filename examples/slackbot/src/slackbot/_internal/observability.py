"""logfire instrumentation for the slackbot.

no-ops when no write token is available, so local dev and tests are unaffected.
"""

import os
from typing import Any

from prefect.blocks.system import Secret
from prefect.logging.loggers import get_logger

from slackbot.settings import settings

logger = get_logger(__name__)

_configured = False


def _resolve_token() -> str | None:
    if token := os.getenv("LOGFIRE_TOKEN"):
        return token
    try:
        return Secret.load(settings.logfire_token_secret_name, _sync=True).get()  # type: ignore[return-value]
    except Exception as exc:
        logger.debug(f"no logfire token available, skipping instrumentation: {exc}")
        return None


def configure_observability(app: Any = None) -> bool:
    """configure logfire and instrument pydantic-ai, mcp, and the fastapi app.

    returns whether instrumentation was enabled. safe to call more than once.
    """
    global _configured
    if _configured:
        return True

    if not (token := _resolve_token()):
        return False

    import logfire

    logfire.configure(
        token=token,
        service_name=settings.logfire_service_name,
        environment=settings.logfire_environment,
    )

    # captures model requests, tool calls, and their arguments/results
    logfire.instrument_pydantic_ai()
    logfire.instrument_mcp()

    if app is not None:
        logfire.instrument_fastapi(app)

    _configured = True
    logger.info(
        f"logfire enabled (service={settings.logfire_service_name}, "
        f"environment={settings.logfire_environment})"
    )
    return True
