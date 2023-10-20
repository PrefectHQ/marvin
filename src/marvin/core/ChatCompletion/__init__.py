from typing import Optional, Any, TypeVar
from .abstract import AbstractChatCompletion

from marvin._compat import BaseModel
from marvin.settings import settings
from openai import ChatCompletion as OriginalChatCompletion

T = TypeVar(
    "T",
    bound=BaseModel,
)

PROVIDER_SHORTCUTS = {
    "gpt-3.5-turbo": "openai",
    "gpt-4": "openai",
    "claude-1": "anthropic",
    "claude-2": "anthropic",
}


def parse_model_shortcut(provider: Optional[str]) -> tuple[str, str]:
    """
    Parse a model string into a provider and a model name.
    - If the provider is None, use the default provider and model.
    - If the provider is a shortcut, use the shortcut to get the provider and model.
    """
    if provider is None:
        try:
            provider, model = settings.llm_model.split("/")
        except Exception:
            provider, model = (
                PROVIDER_SHORTCUTS[str(settings.llm_model)],
                settings.llm_model,
            )

    elif provider in PROVIDER_SHORTCUTS:
        provider, model = PROVIDER_SHORTCUTS[provider], provider
    else:
        provider, model = provider.split("/")
    return provider, model


class ChatCompletion(OriginalChatCompletion):
    def __new__(cls, model: Optional[str] = None, **kwargs: Any):
        provider, model = parse_model_shortcut(model)

        if provider in ("openai", "azure_openai"):
            from .providers.openai import OpenAIChatCompletion

            instance = OpenAIChatCompletion(provider=provider, model=model, **kwargs)

        elif provider == "anthropic":
            from .providers.anthropic import AnthropicChatCompletion

            instance = AnthropicChatCompletion(model=model, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider}")

        return instance

    @classmethod
    def create(cls, _provider: str = "openai", **kwargs):
        return super().create(**(settings.get_defaults(_provider) | kwargs))

    @classmethod
    async def acreate(cls, _provider: str = "openai", **kwargs):
        return await super().acreate(**(settings.get_defaults(_provider) | kwargs))
