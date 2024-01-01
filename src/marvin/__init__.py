from .settings import settings

from .beta.assistants import Assistant
from .beta.assistants.applications import AIApplication

from .components import ai_fn, ai_model, ai_classifier
from .components.prompt.fn import prompt_fn

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

__all__ = [
    "ai_fn",
    "ai_model",
    "ai_classifier",
    "prompt_fn",
    "settings",
    "AIApplication",
    "Assistant",
]
