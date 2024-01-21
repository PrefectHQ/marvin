from .settings import settings

from .ai.text import (
    fn,
    cast,
    cast_async,
    extract,
    extract_async,
    classify,
    classify_async,
    classifier,
    generate,
    generate_async,
    model,
    Model,
)
from .ai.images import paint, image
from .ai.audio import speak, speech
from . import beta

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"


__all__ = [
    # --- text ---
    "Model",
    "cast",
    "cast_async",
    "classify",
    "classify_async",
    "classifier",
    "extract",
    "extract_async" "fn",
    "generate",
    "generate_async",
    "model",
    # --- images ---
    "image",
    "paint",
    # --- audio ---
    "speak",
    "speech",
    # --- beta ---
    "beta",
]


# compatibility with Marvin v1
ai_fn = fn
ai_model = model
ai_classifier = classifier
