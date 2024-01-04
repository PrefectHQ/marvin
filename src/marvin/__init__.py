from .settings import settings

from .components import fn, ai_model, classifier
from .components.prompt.fn import prompt_fn

# compatibility with Marvin v1
from .components import classifier as ai_classifier, fn as ai_fn

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

__all__ = [
    "fn",
    "ai_model",
    "classifier",
    "prompt_fn",
    "settings",
]
