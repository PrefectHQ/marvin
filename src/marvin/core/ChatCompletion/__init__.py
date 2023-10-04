from typing import Optional, Any, TypeVar
from pydantic import BaseModel
from .abstract import AbstractChatCompletion
from marvin.settings import settings

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


def ChatCompletion(
    model: Optional[str] = None,
    **kwargs: Any,
) -> AbstractChatCompletion[T]:  # type: ignore
    provider, model = parse_model_shortcut(model)
    if provider == "openai" or provider == "azure_openai":
        from .providers.openai import OpenAIChatCompletion

        return OpenAIChatCompletion(provider=provider, model=model, **kwargs)
    if provider == "anthropic":
        from .providers.anthropic import AnthropicChatCompletion

        return AnthropicChatCompletion(model=model, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")
