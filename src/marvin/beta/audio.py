"""Utilities for working with audio."""

import collections
import io
import tempfile
import threading
from typing import Callable

from pydantic import BaseModel, Field

from marvin.types import Audio
from marvin.utilities.logging import get_logger

logger = get_logger(__name__)
try:
    import speech_recognition as sr
    from playsound import playsound
except ImportError:
    raise ImportError(
        'Marvin was not installed with the "audio" extra. Please run `pip install'
        ' "marvin[audio]"` to use this module.'
    )


def play_audio(audio: bytes):
    """
    Play audio from bytes.

    Parameters:
        audio (bytes): Audio data in a format that the system can play.
    """
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(audio)
        playsound(temp_file.name)


def record_audio(duration: int = None) -> Audio:
    """
    Record audio from the default microphone to WAV format bytes.

    Waits for a specified duration or until a KeyboardInterrupt occurs.

    Parameters:
        duration (int, optional): Recording duration in seconds. Records indefinitely if None.

    Returns:
        bytes: WAV-formatted audio data.
    """
    with sr.Microphone() as source:
        # this is a modified version of the record method from the Recognizer class
        # that can be keyboard interrupted
        frames = io.BytesIO()
        seconds_per_buffer = (source.CHUNK + 0.0) / source.SAMPLE_RATE
        elapsed_time = 0
        try:
            while True:
                buffer = source.stream.read(source.CHUNK)
                if len(buffer) == 0:
                    break

                elapsed_time += seconds_per_buffer
                if duration and elapsed_time > duration:
                    break

                frames.write(buffer)
        except KeyboardInterrupt:
            logger.debug("Recording interrupted by user")
            pass

        frame_data = frames.getvalue()
        frames.close()
        audio = sr.audio.AudioData(frame_data, source.SAMPLE_RATE, source.SAMPLE_WIDTH)

    return Audio(data=audio.get_wav_data(), format="wav")


def record_phrase(
    after_phrase_silence: float = None,
    timeout: int = None,
    max_phrase_duration: int = None,
    adjust_for_ambient_noise: bool = True,
) -> Audio:
    """
    Record a single speech phrase to WAV format bytes.

    Parameters:
        after_phrase_silence (float, optional): Silence duration to consider speech
            ended. Defaults to 0.8 seconds.
        timeout (int, optional): Max wait time for speech start before giving
            up. None for no timeout.
        max_phrase_duration (int, optional): Max duration for recording a phrase.
            None for no limit.
        adjust_for_ambient_noise (bool, optional): Adjust recognizer sensitivity
            to ambient noise. Defaults to True. (Adds minor latency during
            calibration)

    Returns:
        bytes: WAV-formatted audio data.
    """
    r = sr.Recognizer()
    if after_phrase_silence is not None:
        r.pause_threshold = after_phrase_silence
    with sr.Microphone() as source:
        if adjust_for_ambient_noise:
            r.adjust_for_ambient_noise(source)
        audio = r.listen(source, timeout=timeout, phrase_time_limit=max_phrase_duration)
    return Audio(data=audio.get_wav_data(), format="wav")


class AudioPayload(BaseModel):
    model_config: dict = dict(arbitrary_types_allowed=True)
    audio: Audio
    audio_buffer: list[Audio] = Field(
        description="A buffer of the last 10 audio samples."
    )
    recognizer: sr.Recognizer
    stop: Callable


def record_background(
    callback: Callable[[AudioPayload], None],
    max_phrase_duration: int = None,
    adjust_for_ambient_noise: bool = True,
    default_wait_for_stop: bool = True,
):
    """
    Start a background thread to record phrases and invoke a callback with each.

    Parameters:
        callback (Callable): Function to call with AudioPayload for
            each phrase.
        max_phrase_duration (int, optional): Max phrase duration. None for no
            limit.
        adjust_for_ambient_noise (bool, optional): Adjust sensitivity to ambient
            noise. Defaults to True. (Adds minor latency during calibration)
        default_wait_for_stop (bool, optional): When the stop function is called,
            this determines the default behavior of whether to wait for the
            background thread to finish. Defaults to True.

    Returns:
        Callable: Function to stop background recording.
    """
    r = sr.Recognizer()
    m = sr.Microphone()
    if adjust_for_ambient_noise:
        with m as source:
            r.adjust_for_ambient_noise(source)

    running = [True]

    def stopper(wait_for_stop=None):
        if wait_for_stop is None:
            wait_for_stop = default_wait_for_stop
        running[0] = False
        if wait_for_stop:
            listener_thread.join()  # block until the background thread is done, which can take around 1 second

    def callback_wrapper(payload):
        """Run the callback in a separate thread to avoid blocking."""
        callback_thread = threading.Thread(target=callback, args=(payload,))
        callback_thread.daemon = True
        callback_thread.start()

    def threaded_listen():
        with m as source:
            audio_buffer = collections.deque(maxlen=10)
            while running[0]:
                try:  # listen for 1 second, then check again if the stop function has been called
                    audio = r.listen(source, 1, max_phrase_duration)
                    audio = Audio(data=audio.get_wav_data(), format="wav")
                    audio_buffer.append(audio)
                except sr.exceptions.WaitTimeoutError:
                    # listening timed out, just try again
                    pass
                else:
                    payload = AudioPayload(
                        audio=audio,
                        audio_buffer=audio_buffer,
                        recognizer=r,
                        stop=stopper,
                    )
                    # run callback in thread
                    callback_wrapper(payload)

    listener_thread = threading.Thread(target=threaded_listen)
    listener_thread.daemon = True
    listener_thread.start()
    return stopper


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

    import marvin.beta.audio

    def audio_callback(payload: marvin.beta.audio.AudioPayload) -> None:
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

    stop_fn = marvin.beta.audio.record_background(
        audio_callback, max_phrase_duration=10, default_wait_for_stop=False
    )
    return stop_fn
