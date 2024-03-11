import inspect
from functools import partial, wraps
from pathlib import Path
from typing import IO, Any, Callable, Literal, Optional, TypeVar, Union

import marvin
from marvin.client.openai import AsyncMarvinClient
from marvin.types import Audio, HttpxBinaryResponseContent, SpeechRequest
from marvin.utilities.asyncio import run_sync
from marvin.utilities.jinja import Environment
from marvin.utilities.logging import get_logger
from marvin.utilities.python import PythonFunction

T = TypeVar("T")

logger = get_logger(__name__)


async def generate_speech(
    prompt_template: str,
    prompt_kwargs: Optional[dict[str, Any]] = None,
    model_kwargs: Optional[dict[str, Any]] = None,
) -> Audio:
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
    response = await AsyncMarvinClient().generate_speech(**request.model_dump())
    data = response.read()
    return Audio(data=data, format="mp3")


async def speak_async(
    text: str,
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = None,
    model_kwargs: Optional[dict[str, Any]] = None,
) -> Audio:
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
        Audio: The generated audio.
    """
    model_kwargs = model_kwargs or {}
    if voice is not None:
        model_kwargs["voice"] = voice

    response = await generate_speech(
        prompt_template=text,
        model_kwargs=model_kwargs,
    )
    return response


def speak(
    text: str,
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = None,
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
    return run_sync(speak_async(text, voice, model_kwargs))


async def transcribe_async(
    data: Union[Path, bytes, IO[bytes], Audio],
    prompt: str = None,
    model_kwargs: Optional[dict[str, Any]] = None,
) -> str:
    """
    Transcribes audio from a file.

    This function converts audio from a file to text.
    """

    if isinstance(data, Audio):
        data = data.data

    transcript = await AsyncMarvinClient().generate_transcript(
        file=data, prompt=prompt, **model_kwargs or {}
    )
    return transcript.text


def transcribe(
    data: Union[Path, bytes, IO[bytes], Audio],
    prompt: str = None,
    model_kwargs: Optional[dict[str, Any]] = None,
) -> str:
    """
    Transcribes audio from a file.

    This function converts audio from a file to text.
    """
    return run_sync(transcribe_async(data=data, prompt=prompt, **model_kwargs or {}))


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
    async def async_wrapper(*args, **kwargs):
        model = PythonFunction.from_function_call(fn, *args, **kwargs)
        return await speak_async(
            text=model.return_value, voice=voice, model_kwargs=model_kwargs
        )

    if inspect.iscoroutinefunction(fn):
        return async_wrapper
    else:

        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            return run_sync(async_wrapper(*args, **kwargs))

        return sync_wrapper
