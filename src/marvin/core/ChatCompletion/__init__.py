from marvin.pydantic import validate_arguments
from typing import Literal
from marvin.utilities.module_loading import import_string

models = {
    "gpt-3.5-turbo": ("marvin.core.ChatCompletion.providers.openai", "gpt-3.5-turbo"),
    "gpt-4": (
        "marvin.core.ChatCompletion.providers.openai",
        "gpt-4",
    ),
    "claude-1": ("marvin.core.ChatCompletion.providers.anthropic", "claude-1"),
    "claude-2": ("marvin.core.ChatCompletion.providers.anthropic", "claude-2"),
}


@validate_arguments
def ChatCompletion(model: Literal[*models.keys()], **kwargs):
    path, model = models.get(model, None)
    module = import_string(f"{path}.ChatCompletion")
    return module(_defaults={"model": model, **kwargs})
