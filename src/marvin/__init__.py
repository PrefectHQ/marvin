from .settings import settings

from .components import ai_fn, ai_model

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

__all__ = [
    "ai_fn",
    "settings",
]
