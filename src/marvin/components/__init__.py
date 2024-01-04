from .function import fn, Function
from .classifier import classifier, Classifier
from .model import model
from .image import image
from .speech import speech
from .prompt.fn import prompt_fn, PromptFunction

__all__ = [
    "fn",
    "classifier",
    "model",
    "image",
    "prompt_fn",
    "Function",
    "Classifier",
    "PromptFunction",
]
