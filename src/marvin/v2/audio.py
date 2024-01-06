from functools import wraps
from typing import Callable, TypeVar

from openai._base_client import HttpxBinaryResponseContent

from marvin.requests import SpeechRequest
from marvin.utilities.jinja import Environment
from marvin.utilities.python import PythonFunction
from marvin.v2.client import MarvinClient

T = TypeVar("T")


def generate_speech(
    prompt_template: str,
    prompt_kwargs: dict = None,
    model_kwargs: dict = None,
) -> HttpxBinaryResponseContent:
    prompt_kwargs = prompt_kwargs or {}
    model_kwargs = model_kwargs or {}
    prompt = Environment.render(prompt_template, **prompt_kwargs)
    request = SpeechRequest(input=prompt, **model_kwargs)
    response = MarvinClient().generate_speech(**request.model_dump())
    return response


def speak(text: str, model_kwargs: dict = None):
    """
    Use an AI to generate audio from text.
    """
    response = generate_speech(
        prompt_template=text,
        model_kwargs=model_kwargs,
    )
    return response


def speech(fn: Callable):
    """
    Function decorator that generates audio from the wrapped function's return
    value.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        model = PythonFunction.from_function_call(fn, *args, **kwargs)
        return speak(text=model.return_value)

    return wrapper
