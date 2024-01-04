from .settings import settings

from .components import ai_fn, ai_model, ai_classifier, ai_image
from .components.prompt.fn import prompt_fn

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

__all__ = [
    "ai_fn",
    "ai_model",
    "ai_classifier",
    "ai_image",
    "prompt_fn",
    "settings",
]
