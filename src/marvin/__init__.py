from .settings import settings

from .ai.text import fn, cast, extract, classify, classifier, generate, model, Model
from .ai.images import paint, image
from .ai.audio import speak, speech


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
ai_fn = fn
ai_model = model
ai_classifier = classifier
