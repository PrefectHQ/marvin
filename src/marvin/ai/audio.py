import inspect
from functools import partial, wraps
from pathlib import Path
from typing import IO, Any, Callable, Literal, Optional, TypeVar, Union

import marvin
from marvin.client.openai import get_default_async_client
from marvin.types import Audio, SpeechRequest
from marvin.utilities.asyncio import run_sync
from marvin.utilities.jinja import Environment
from marvin.utilities.logging import get_logger
from marvin.utilities.python import PythonFunction

T = TypeVar("T")

logger = get_logger(__name__)


async def generate_speech(
    prompt_template: str,
    prompt_kwargs: Optional[dict[str, Any]] = None,
    stream: bool = True,
    model_kwargs: Optional[dict[str, Any]] = None,
) -> Audio:
    """
    Generates speech based on a provided prompt template.

    This function uses the OpenAI Audio API to generate speech based on a provided
    prompt template. The function supports additional arguments for the prompt
    and the model.

    Args:
        prompt_template (str): The template for the prompt.
        prompt_kwargs (dict, optional): Additional keyword arguments for the
            prompt. Defaults to None.
        stream (bool, optional): Whether to stream the audio. If False, the
            audio can not be saved or played until it has all been generated. If
            True, `.save()` and `.play()` can be called immediately.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.

    Returns:
        Audio: The response from the OpenAI Audio API, which includes the
            generated speech.
    """

    if stream and "response_format" not in model_kwargs:
        model_kwargs["response_format"] = "pcm"

    client = get_default_async_client()
    prompt_kwargs = prompt_kwargs or {}
    model_kwargs = model_kwargs or {}
    prompt = Environment.render(prompt_template, **prompt_kwargs)
    request = SpeechRequest(input=prompt, **model_kwargs)
    if marvin.settings.log_verbose:
        getattr(logger, "debug_kv")("Request", request.model_dump_json(indent=2))

    if stream:
        if request.response_format != "pcm":
            raise ValueError(
                "Streaming audio is only supported for the PCM format. When you "
                "call e.g. `.save('audio.mp3')`, Marvin can convert PCM-streamed "
                "audio to any other format."
            )
        response = client.generate_speech_streaming(**request.model_dump())
        return Audio.from_stream(response, format=request.response_format)
    else:
        response = await client.generate_speech(**request.model_dump())
        data = response.read()
        return Audio(data=data, format=request.response_format)


async def speak_async(
    text: str,
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = None,
    stream: bool = True,
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
        stream (bool, optional): Whether to stream the audio. If False, the
            audio can not be saved or played until it has all been generated. If
            True, `.save()` and `.play()` can be called immediately.
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
        stream=stream,
        model_kwargs=model_kwargs,
    )
    return response


def speak(
    text: str,
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = None,
    stream: bool = True,
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
        stream (bool, optional): Whether to stream the audio. If False, the
            audio can not be saved or played until it has all been generated. If
            True, `.save()` and `.play()` can be called immediately.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.

    Returns:
        Audio: The generated audio.
    """
    return run_sync(
        speak_async(text=text, voice=voice, stream=stream, model_kwargs=model_kwargs)
    )


async def transcribe_async(
    data: Union[Path, bytes, IO[bytes], Audio],
    prompt: str = None,
    model_kwargs: Optional[dict[str, Any]] = None,
) -> str:
    """
    Transcribes audio from a file.

    This function converts audio from a file to text.
    """

    client = get_default_async_client()

    if isinstance(data, Audio):
        data = data.data

    transcript = await client.generate_transcript(
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
    stream: bool = True,
    model_kwargs: Optional[dict] = None,
) -> Callable:
    """
    Function decorator that generates audio from the wrapped function's return
    value. The voice used for the audio can be specified.

    Args:
        fn (Callable, optional): The function to wrap. Defaults to None.
        voice (str, optional): The voice to use for the audio. Defaults to None.
        stream (bool, optional): Whether to stream the audio. If False, the
            audio can not be saved or played until it has all been generated. If
            True, `.save()` and `.play()` can be called immediately.

    Returns:
        Callable: The wrapped function.
    """
    if fn is None:
        return partial(speech, voice=voice, stream=stream, model_kwargs=model_kwargs)

    @wraps(fn)
    async def async_wrapper(*args, **kwargs):
        model = PythonFunction.from_function_call(fn, *args, **kwargs)
        return await speak_async(
            text=model.return_value,
            voice=voice,
            stream=stream,
            model_kwargs=model_kwargs,
        )

    if inspect.iscoroutinefunction(fn):
        return async_wrapper
    else:

        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            return run_sync(async_wrapper(*args, **kwargs))

        return sync_wrapper
