from .settings import settings

from .core.text import fn, cast, extract, classify, classifier, generate, model, Model
from .core.images import paint, image
from .core.audio import speak, speech


try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"


__all__ = [
    # --- text ---
    "Model",
    "cast",
    "classify",
    "classifier",
    "extract",
    "fn",
    "generate",
    "model",
    # --- images ---
    "image",
    "paint",
    # --- audio ---
    "speak",
    "speech",
]


# compatibility with Marvin v1
from marvin.core._v1_compat import ai_fn, ai_model, ai_classifier
