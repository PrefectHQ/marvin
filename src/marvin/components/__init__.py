from .function import fn, Function
from .classifier import classifier, Classifier
from .model import model
from .image import image, Image
from .prompt.fn import prompt_fn, PromptFunction

__all__ = [
    "fn",
    "classifier",
    "model",
    "image",
    "prompt_fn",
    "Image",
    "Function",
    "Classifier",
    "PromptFunction",
]
