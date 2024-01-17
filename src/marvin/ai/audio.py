from functools import partial, wraps
from typing import Any, Callable, Literal, Optional, TypeVar

import marvin
from marvin.client.openai import MarvinClient
from marvin.types import HttpxBinaryResponseContent, SpeechRequest
from marvin.utilities.jinja import Environment
from marvin.utilities.logging import get_logger
from marvin.utilities.python import PythonFunction

T = TypeVar("T")

logger = get_logger(__name__)


def generate_speech(
    prompt_template: str,
    prompt_kwargs: Optional[dict[str, Any]] = None,
    model_kwargs: Optional[dict[str, Any]] = None,
) -> HttpxBinaryResponseContent:
    """
    Generates an image based on a provided prompt template.

    This function uses the DALL-E API to generate an image based on a provided
    prompt template. The function supports additional arguments for the prompt
    and the model.

    Args:
        prompt_template (str): The template for the prompt.
        prompt_kwargs (dict, optional): Additional keyword arguments for the
            prompt. Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.

    Returns:
        ImagesResponse: The response from the DALL-E API, which includes the
            generated image.
    """
    prompt_kwargs = prompt_kwargs or {}
    model_kwargs = model_kwargs or {}
    prompt = Environment.render(prompt_template, **prompt_kwargs)
    request = SpeechRequest(input=prompt, **model_kwargs)
    if marvin.settings.log_verbose:
        getattr(logger, "debug_kv")("Request", request.model_dump_json(indent=2))
    response = MarvinClient().generate_speech(**request.model_dump())
    if marvin.settings.log_verbose:
        getattr(logger, "debug_kv")("Response", response.model_dump_json(indent=2))
    return response


def speak(
    text: str,
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "alloy",
    model_kwargs: Optional[dict[str, Any]] = None,
) -> HttpxBinaryResponseContent:
    """
    Generates audio from text using an AI.

    This function uses an AI to generate audio from the provided text. The voice
    used for the audio can be specified.

    Args:
        text (str): The text to generate audio from.
        voice (Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"], optional):
            The voice to use for the audio. Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.

    Returns:
        HttpxBinaryResponseContent: The generated audio.
    """
    model_kwargs = model_kwargs or {}
    if voice is not None:
        model_kwargs["voice"] = voice

    response = generate_speech(
        prompt_template=text,
        model_kwargs=model_kwargs,
    )
    return response


def speech(
    fn: Optional[Callable] = None,
    *,
    voice: Optional[str] = None,
    model_kwargs: Optional[dict] = None,
) -> Callable:
    """
    Function decorator that generates audio from the wrapped function's return
    value. The voice used for the audio can be specified.

    Args:
        fn (Callable, optional): The function to wrap. Defaults to None.
        voice (str, optional): The voice to use for the audio. Defaults to None.

    Returns:
        Callable: The wrapped function.
    """
    if fn is None:
        return partial(speech, voice=voice, model_kwargs=model_kwargs)

    @wraps(fn)
    def wrapper(*args, **kwargs):
        model = PythonFunction.from_function_call(fn, *args, **kwargs)
        return speak(text=model.return_value, voice=voice, model_kwargs=model_kwargs)

    return wrapper
