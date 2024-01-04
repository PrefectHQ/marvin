from .function import fn, Function
from .classifier import classifier, Classifier
from .model import model
from .ai_image import ai_image, AIImage
from .prompt.fn import prompt_fn, PromptFunction

__all__ = [
    "fn",
    "classifier",
    "model",
    "ai_image",
    "prompt_fn",
    "AIImage",
    "Function",
    "Classifier",
    "PromptFunction",
]
