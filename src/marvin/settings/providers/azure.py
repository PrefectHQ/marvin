from typing import Any, Awaitable, Callable, Literal

from pydantic import Field, SecretStr, create_model

from ..._compat import V1Field, model_dump  # type: ignore[import-private]
from ...core.ChatCompletion import BaseChatCompletion, ChatCompletionConfig
from .base import MarvinBaseSettings


class AzureOpenAIBaseSettings(MarvinBaseSettings):
    api_type: Literal["azure", "azure_ad"] = "azure"

    api_base: str | None = Field(
        default=None,
        description=(
            "The endpoint of the Azure OpenAI API. This should have the form"
            " https://YOUR_RESOURCE_NAME.openai.azure.com"
        ),
    )
    api_version: str | None = Field(
        default="2023-07-01-preview", description="The API version"
    )

    api_key: SecretStr | None = V1Field(
        default=None,
        env=[
            "MARVIN_AZURE_API_KEY",
            "MARVIN_OPENAI_API_KEY",
            "OPENAI_API_KEY",
            "AZURE_API_KEY",
        ],
    )

    deployment_name: str | None = Field(
        default=None,
        description=(
            "This will correspond to the custom name you chose for your deployment when"
            " you deployed a model."
        ),
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
            **{
                **model_dump(
                    self,
                    exclude_none=True,
                    exclude={"api_key", "embedding_engine"},
                ),
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
        env_prefix = "MARVIN_AZURE_OPENAI_"
