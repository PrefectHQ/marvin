from typing import Any, Awaitable, Callable

from pydantic import Field, SecretStr, create_model

from ..._compat import V1Field, model_dump  # type: ignore[import-private]
from ...core.ChatCompletion import BaseChatCompletion, ChatCompletionConfig
from .base import MarvinBaseSettings


class AnthropicBaseSettings(MarvinBaseSettings):
    api_key: SecretStr | None = V1Field(
        default=None, env=["MARVIN_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"]
    )

    model: str | None = Field(
        default="claude-instant-1", description="The default model to use"
    )  # noqa

    def get_client_params(
        self,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if api_key:
            return {"api_key": api_key, **kwargs}
        elif self.api_key is None:
            return kwargs
        else:
            return {"api_key": self.api_key.get_secret_value(), **kwargs}

    def get_request_params(self, **kwargs: Any) -> dict[str, Any]:
        from marvin.settings import settings  # type: ignore

        return {
            "max_tokens_to_sample": settings.llm_max_tokens,
            "temperature": settings.llm_temperature,
            "timeout": settings.llm_request_timeout_seconds,
            **kwargs,
        }

    def get_create(self, api_key: str | None = None) -> Callable[..., Any]:
        from anthropic import Anthropic

        return Anthropic(**self.get_client_params(api_key)).completions.create

    def get_acreate(self, api_key: str | None = None) -> Callable[..., Awaitable[Any]]:
        from anthropic import AsyncAnthropic

        return AsyncAnthropic(**self.get_client_params(api_key)).completions.create

    def ChatCompletionConfig(
        self,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> ChatCompletionConfig:
        return create_model(
            "ChatCompletionConfig",
            __base__=ChatCompletionConfig,
            create=self.get_create(api_key=api_key),
            acreate=self.get_acreate(api_key=api_key),
        )(
            **{
                **model_dump(self, exclude_none=True, exclude={"api_key"}),
                **self.get_request_params(**kwargs),
            }
        )

    def ChatCompletion(
        self,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> BaseChatCompletion:
        return BaseChatCompletion(
            defaults=self.ChatCompletionConfig(api_key=api_key, **kwargs)
        )

    class Config(MarvinBaseSettings.Config):
        env_prefix = "MARVIN_ANTHROPIC_"
