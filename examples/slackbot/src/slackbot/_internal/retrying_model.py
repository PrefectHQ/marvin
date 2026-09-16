"""Retry transient provider failures without replaying completed agent tools."""

import asyncio

from prefect.logging.loggers import get_logger
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.settings import ModelSettings

logger = get_logger(__name__)
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504, 529}


class RetryingModel(WrapperModel):
    """Allow two delayed retries of a non-streaming model request.

    The provider SDK may also perform its own bounded transport retries.
    Cancellation, authentication errors, and malformed requests propagate.
    """

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        for attempt in range(3):
            try:
                return await self.wrapped.request(
                    messages, model_settings, model_request_parameters
                )
            except ModelHTTPError as exc:
                if exc.status_code not in TRANSIENT_STATUS_CODES or attempt == 2:
                    raise
                delay = (1, 3)[attempt]
                logger.warning(
                    "Retrying model request after HTTP %s (retry %s/2 in %ss)",
                    exc.status_code,
                    attempt + 1,
                    delay,
                )
                await asyncio.sleep(delay)
        raise AssertionError("Unreachable")
