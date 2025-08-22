from __future__ import annotations

import os
from typing import overload

from httpx import AsyncClient as AsyncHTTPClient
from openai import AsyncOpenAI

from pydantic_ai.exceptions import UserError
from pydantic_ai.models import cached_async_http_client
from pydantic_ai.profiles import ModelProfile
from pydantic_ai.profiles.openai import openai_model_profile
from pydantic_ai.providers import Provider


class AIMLAPIProvider(Provider[AsyncOpenAI]):
    """Provider for the AI/ML API."""

    @property
    def name(self) -> str:  # pragma: no cover - simple property
        return "aimlapi"

    @property
    def base_url(self) -> str:  # pragma: no cover - simple property
        return "https://api.aimlapi.com/v1"

    @property
    def client(self) -> AsyncOpenAI:
        return self._client

    def model_profile(self, model_name: str) -> ModelProfile | None:  # pragma: no cover - thin wrapper
        return openai_model_profile(model_name)

    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, *, api_key: str) -> None: ...

    @overload
    def __init__(self, *, api_key: str, http_client: AsyncHTTPClient) -> None: ...

    @overload
    def __init__(self, *, openai_client: AsyncOpenAI | None = None) -> None: ...

    def __init__(
        self,
        *,
        api_key: str | None = None,
        openai_client: AsyncOpenAI | None = None,
        http_client: AsyncHTTPClient | None = None,
    ) -> None:
        api_key = api_key or os.getenv("AIML_API_KEY")
        if not api_key and openai_client is None:
            raise UserError(
                "Set the `AIML_API_KEY` environment variable or pass it via `AIMLAPIProvider(api_key=...)` "
                "to use the AI/ML API provider."
            )

        if openai_client is not None:
            self._client = openai_client
        elif http_client is not None:
            self._client = AsyncOpenAI(base_url=self.base_url, api_key=api_key, http_client=http_client)
        else:
            http_client = cached_async_http_client(provider="aimlapi")
            self._client = AsyncOpenAI(base_url=self.base_url, api_key=api_key, http_client=http_client)
