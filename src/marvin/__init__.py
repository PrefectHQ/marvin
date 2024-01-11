from .settings import settings

from .apis.text import fn, cast, extract, classify, classifier, generate, model, Model
from .apis.images import paint, image
from .apis.audio import speak, speech


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
from marvin.apis._v1_compat import ai_fn, ai_model, ai_classifier
