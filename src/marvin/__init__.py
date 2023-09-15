from .settings import settings
from .components import (
    ai_classifier,
    ai_fn,
    ai_model,
    AIApplication,
    AIFunction,
    AIModel,
    AIModelFactory,
)

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"


from .core.ChatCompletion import ChatCompletion

__all__ = [
    "ai_classifier",
    "ai_fn",
    "ai_model",
    "AIApplication",
    "AIFunction",
    "AIModel",
    "AIModelFactory",
    "settings",
]
