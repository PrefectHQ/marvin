from typing import Any, Awaitable, Callable

from pydantic import Field, SecretStr, create_model

from ..._compat import V1Field, _model_dump  # type: ignore[import-private]
from ...core.ChatCompletion import BaseChatCompletion, ChatCompletionConfig
from .base import MarvinBaseSettings


class OpenAIBaseSettings(MarvinBaseSettings):
    organization: str | None = Field(
        default=None, description="The organization name"
    )  # noqa
    embedding_engine: str = Field(default="text-embedding-ada-002")
    api_type: str | None = Field(default=None)
    api_base: str | None = Field(
        default=None, description="The endpoint the OpenAI API."
    )  # noqa
    api_version: str | None = Field(default=None, description="The API version")
    model: str | None = Field(
        default="gpt-3.5-turbo", description="The default model to use"
    )  # noqa

    api_key: SecretStr | None = V1Field(
        default=None,
        env=["MARVIN_OPENAI_API_KEY", "OPENAI_API_KEY"],
    )

    def get_request_params(
        self, api_key: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        from marvin.settings import settings  # type: ignore

        api_params: dict[str, Any] = {}
        if api_key:
            api_params = {"api_key": api_key, **kwargs}
        elif self.api_key is None:
            pass
        else:
            api_params = {"api_key": self.api_key.get_secret_value()}
        return {
            "max_tokens": settings.llm_max_tokens,
            "temperature": settings.llm_temperature,
            "request_timeout": settings.llm_request_timeout_seconds,
            **api_params,
            **kwargs,
        }

    def get_create(self, api_key: str | None = None) -> Callable[..., Any]:
        from openai import ChatCompletion

        return ChatCompletion.create  # type: ignore

    def get_acreate(self, api_key: str | None = None) -> Callable[..., Awaitable[Any]]:
        from openai import ChatCompletion

        return ChatCompletion.acreate  # type: ignore

    def ChatCompletionConfig(
        self,
        **kwargs: Any,
    ) -> ChatCompletionConfig:
        return create_model(
            "ChatCompletionConfig",
            __base__=ChatCompletionConfig,
            create=self.get_create(),
            acreate=self.get_acreate(),
        )(
            **_model_dump(
                self,
                mode="python",
                exclude_none=True,
                exclude={"api_key", "embedding_engine"},
            ),
            **self.get_request_params(**kwargs),
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
        env_prefix = "MARVIN_OPENAI_"
