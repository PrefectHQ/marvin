import collections
from typing import Callable

from marvin.utilities.logging import get_logger

logger = get_logger(__name__)


def transcribe_live(callback: Callable[[str], None] = None) -> Callable[[], None]:
    """
    Starts a live transcription service that transcribes audio in real-time and
    calls a callback function with the transcribed text.

    The function starts a background task in a thread that continuously records audio and
    transcribes it into text. The transcribed text is then passed to the
    provided callback function. Note that the callback must be threadsafe.

    Args:
        callback (Callable[[str], None], optional): A function that is called
            with the transcribed text as its argument. If no callback is provided,
            the transcribed text will be printed to the console. Defaults to None.

    Returns:
        Callable[[], None]: A function that, when called, stops the background
            transcription service.
    """
    if callback is None:
        callback = lambda t: print(f">> {t}")  # noqa E731
    transcription_buffer = collections.deque(maxlen=3)

    import marvin.audio

    def audio_callback(payload: marvin.audio.AudioPayload) -> None:
        buffer_str = (
            "\n\n".join(transcription_buffer)
            if transcription_buffer
            else "<no audio received yet>"
        )
        transcription = marvin.transcribe(
            payload.audio,
            prompt=(
                "The audio is being spoken directly into the microphone. For context"
                " only, here is the transcription up to this point. Do not simply"
                f" repeat it.  \n\n<START HISTORY>\n\n{buffer_str}\n\n<END HISTORY>\n\n"
            ),
        )
        transcription_buffer.append(transcription or "")
        if transcription:
            callback(transcription)

    stop_fn = marvin.audio.record_background(
        audio_callback, max_phrase_duration=10, default_wait_for_stop=False
    )
    return stop_fn
