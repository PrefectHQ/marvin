from .settings import settings

from .components import fn, image, speech, model, cast, extract, classify
from .components.prompt.fn import prompt_fn

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

__all__ = [
    "fn",
    "image",
    "model",
    "cast",
    "extract",
    "classify",
    "speech",
    "prompt_fn",
    "settings",
]


# compatibility with Marvin v1
from .components import classifier as ai_classifier, fn as ai_fn, model as ai_model
