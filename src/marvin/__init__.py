from .settings import Settings

settings = Settings()

from .primitives import ai_fn, ai_application, ai_model, ai_model_factory


__all__ = ["ai_fn", "ai_application", "ai_model", "ai_model_factory", "settings"]
