from .settings import settings

from .ai.text import (
    fn,
    cast,
    cast_async,
    extract,
    extract_async,
    classify,
    classify_async,
    caption,
    caption_async,
    classifier,
    generate,
    generate_async,
    model,
    Model,
    Image,
)
from .ai.images import paint, paint_async, image
from .ai.audio import speak_async, speak, speech, transcribe, transcribe_async

if settings.auto_import_beta_modules:
    from . import beta

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"


__all__ = [
    # --- text ---
    "Model",
    "Image",
    "cast",
    "cast_async",
    "caption",
    "caption_async",
    "classify",
    "classify_async",
    "classifier",
    "extract",
    "extract_async",
    "fn",
    "generate",
    "generate_async",
    "model",
    # --- images ---
    "image",
    "paint",
    "paint_async",
    # --- audio ---
    "speak",
    "speak_async",
    "speech",
    "transcribe",
    "transcribe_async",
    # --- beta ---
]

if settings.auto_import_beta_modules:
    __all__.append("beta")

# compatibility with Marvin v1
ai_fn = fn
ai_model = model
ai_classifier = classifier
