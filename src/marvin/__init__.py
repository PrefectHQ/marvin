from .settings import settings

from .components import fn, classifier, image, speech, model, cast, extract
from .components.prompt.fn import prompt_fn

# compatibility with Marvin v1
from .components import classifier as ai_classifier, fn as ai_fn, model as ai_model

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

__all__ = [
    "fn",
    "classifier",
    "image",
    "model",
    "cast",
    "extract",
    "speech",
    "prompt_fn",
    "settings",
]
