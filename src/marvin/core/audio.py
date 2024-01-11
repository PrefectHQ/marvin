from functools import wraps
from typing import Callable, Literal, TypeVar

from openai._base_client import HttpxBinaryResponseContent

import marvin
from marvin.client.openai import MarvinClient
from marvin.requests import SpeechRequest
from marvin.utilities.jinja import Environment
from marvin.utilities.logging import get_logger
from marvin.utilities.python import PythonFunction

T = TypeVar("T")

logger = get_logger(__name__)


def generate_speech(
    prompt_template: str,
    prompt_kwargs: dict = None,
    model_kwargs: dict = None,
) -> HttpxBinaryResponseContent:
    prompt_kwargs = prompt_kwargs or {}
    model_kwargs = model_kwargs or {}
    prompt = Environment.render(prompt_template, **prompt_kwargs)
    request = SpeechRequest(input=prompt, **model_kwargs)
    if marvin.settings.log_verbose:
        logger.debug_kv("Request", request.model_dump_json(indent=2))
    response = MarvinClient().generate_speech(**request.model_dump())
    if marvin.settings.log_verbose:
        logger.debug_kv("Request", request.model_dump_json(indent=2))
    return response


def speak(
    text: str,
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = None,
    model_kwargs: dict = None,
):
    """
    Use an AI to generate audio from text.
    """
    model_kwargs = model_kwargs or {}
    if voice is not None:
        model_kwargs["voice"] = voice

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
