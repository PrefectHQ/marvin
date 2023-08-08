import marvin

_provider_shortcuts = {
    "gpt-3.5-turbo": "openai",
    "gpt-4": "openai",
    "claude-1": "anthropic",
    "claude-2": "anthropic",
}


def ChatCompletion(model: str = None, **kwargs):
    if model is None:
        model = marvin.settings.llm_model

    if model in _provider_shortcuts:
        provider, model = _provider_shortcuts[model], model
    else:
        provider, model = model.split("/", 1)

    if provider == "openai":
        from marvin.core.ChatCompletion.providers.openai import (
            ChatCompletion as completion_cls,
        )

    elif provider == "anthropic":
        from marvin.core.ChatCompletion.providers.anthropic import (
            ChatCompletion as completion_cls,
        )

    elif provider == "azure_openai":
        from marvin.core.ChatCompletion.providers.azure.openai import (
            ChatCompletion as completion_cls,
        )

    else:
        raise ValueError(f"Unknown provider: {provider}")

    return completion_cls(**kwargs)
