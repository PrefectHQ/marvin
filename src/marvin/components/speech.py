from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Optional,
    TypeVar,
)

from typing_extensions import Literal, ParamSpec

if TYPE_CHECKING:
    from openai._base_client import HttpxBinaryResponseContent

T = TypeVar("T")

P = ParamSpec("P")


def speak(
    input: str,
    *,
    create: Optional[Callable[..., "HttpxBinaryResponseContent"]] = None,
    model: Optional[str] = "tts-1-hd",
    voice: Optional[
        Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    ] = None,
    response_format: Optional[Literal["mp3", "opus", "aac", "flac"]] = None,
    speed: Optional[float] = None,
    filepath: Path,
) -> None:
    if create is None:
        from marvin.settings import settings

        create = settings.openai.audio.speech.create
    return create(
        input=input,
        **({"model": model} if model else {}),
        **({"voice": voice} if voice else {}),
        **({"response_format": response_format} if response_format else {}),
        **({"speed": speed} if speed else {}),
    ).stream_to_file(filepath)


async def aspeak(
    input: str,
    *,
    acreate: Optional[
        Callable[..., Coroutine[Any, Any, "HttpxBinaryResponseContent"]]
    ] = None,
    model: Optional[str],
    voice: Optional[
        Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    ] = None,
    response_format: Optional[Literal["mp3", "opus", "aac", "flac"]] = None,
    speed: Optional[float] = None,
    filepath: Path,
) -> None:
    if acreate is None:
        from marvin.settings import settings

        acreate = settings.openai.audio.speech.acreate
    return (
        await acreate(
            input=input,
            **({"model": model} if model else {}),
            **({"voice": voice} if voice else {}),
            **({"response_format": response_format} if response_format else {}),
            **({"speed": speed} if speed else {}),
        )
    ).stream_to_file(filepath)
