"""Utilities for working with audio."""

import io
import queue
import threading
from typing import Iterator, Optional

import pydub.playback

from marvin.types import Audio
from marvin.utilities.logging import get_logger

try:
    import pyaudio
    import pydub
    import pydub.silence
    import speech_recognition as sr


except ImportError:
    raise ImportError(
        'Marvin was not installed with the "audio" extra. Please run `pip install'
        ' "marvin[audio]"` to use this module.'
    )

logger = get_logger(__name__)


def convert_audio(audio: bytes, from_format: str, to_format: str) -> bytes:
    if from_format == to_format:
        return audio

    temp_file = io.BytesIO(audio)
    temp_file.seek(0)
    segment = pydub.AudioSegment.from_file(
        temp_file,
        format=from_format,
        sample_width=2,
        channels=1,
        frame_rate=24000,
    )

    buffer = io.BytesIO()
    segment.export(buffer, format=to_format)
    buffer.seek(0)

    return buffer.read()


def play_audio(audio: bytes, format="pcm"):
    """
    Play audio from bytes. The proper format must be provided.

    Parameters:
        audio (bytes): Audio data in a format that the system can play.
    """
    wav = convert_audio(audio, format, "wav")
    buffer = io.BytesIO(wav)
    buffer.seek(0)

    wav = pydub.AudioSegment.from_file(
        buffer,
        format="wav",
        sample_width=2,
        channels=1,
        frame_rate=24000,
    )
    pydub.playback.play(wav)


async def stream_audio(audio: Iterator[bytes]):
    """
    Stream audio from an iterator of bytes. Audio chunks must be in `pcm` format.
    """
    player_stream = pyaudio.PyAudio().open(
        format=pyaudio.paInt16, channels=1, rate=24000, output=True
    )
    async for chunk in audio:
        player_stream.write(chunk)


def record(duration: int = None) -> Audio:
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
        logger.info("Recording...")
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
        logger.info("Recording finished.")

        frame_data = frames.getvalue()
        frames.close()
        audio = sr.audio.AudioData(frame_data, source.SAMPLE_RATE, source.SAMPLE_WIDTH)

    return audio


def record_phrase(
    after_phrase_silence: float = None,
    timeout: int = None,
    max_phrase_duration: int = None,
    adjust_for_ambient_noise: bool = False,
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
        logger.info("Recording...")
        audio = r.listen(source, timeout=timeout, phrase_time_limit=max_phrase_duration)
        logger.info("Recording finished.")
    return Audio(data=audio.get_wav_data(), format="wav")


def remove_silence(audio: sr.AudioData) -> Optional[Audio]:
    # Convert the recorded audio data to a pydub AudioSegment
    audio_segment = pydub.AudioSegment(
        data=audio.get_wav_data(),
        sample_width=audio.sample_width,
        frame_rate=audio.sample_rate,
        channels=1,
    )

    # Adjust the silence threshold and minimum silence length as needed
    silence_threshold = -40  # dB
    min_silence_len = 400  # milliseconds

    # Split the audio_segment where silence is detected
    chunks = pydub.silence.split_on_silence(
        audio_segment,
        min_silence_len=min_silence_len,
        silence_thresh=silence_threshold,
        keep_silence=100,
    )

    if chunks:
        return Audio(data=sum(chunks).raw_data, format="wav")


class BackgroundAudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.queue = queue.Queue()
        self._stop_event = None
        self._thread = None

    def __len__(self) -> int:
        return self.queue.qsize()

    def stream(self) -> "BackgroundAudioStream":
        return BackgroundAudioStream(self)

    def _record_thread(
        self, max_phrase_duration: Optional[int], adjust_for_ambient_noise: bool
    ):
        r = sr.Recognizer()
        m = sr.Microphone()
        with m as source:
            if adjust_for_ambient_noise:
                r.adjust_for_ambient_noise(source)

            logger.info("Recording started.")
            while not self._stop_event.is_set():
                try:
                    audio = r.listen(
                        source, timeout=1, phrase_time_limit=max_phrase_duration
                    )
                    if processed_audio := remove_silence(audio):
                        self.queue.put(processed_audio)
                # listening timed out, just try again
                except sr.exceptions.WaitTimeoutError:
                    continue

    def start(
        self,
        max_phrase_duration: int = None,
        adjust_for_ambient_noise: bool = True,
        clear_queue: bool = False,
    ):
        if self.is_recording:
            raise ValueError("Recording is already in progress.")
        if max_phrase_duration is None:
            max_phrase_duration = 5
        if clear_queue:
            self.queue.queue.clear()
        self.is_recording = True
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._record_thread,
            args=(max_phrase_duration, adjust_for_ambient_noise),
        )
        self._thread.daemon = True
        self._thread.start()

    def stop(self, wait: bool = True):
        if not self.is_recording:
            raise ValueError("Recording is not in progress.")
        self._stop_event.set()
        if wait:
            self._thread.join()
        logger.info("Recording finished.")
        self._is_recording = False


class BackgroundAudioStream:
    def __init__(self, recorder: BackgroundAudioRecorder):
        self.recorder = recorder

    def __len__(self) -> int:
        return self.recorder.queue.qsize()

    def __iter__(self) -> "BackgroundAudioStream":
        return self

    def __next__(self) -> Audio:
        while True:
            if not self.recorder.is_recording and self.recorder.queue.empty():
                raise StopIteration
            try:
                return self.recorder.queue.get(timeout=0.25)
            except queue.Empty:
                continue


def record_background(
    max_phrase_duration: int = None, adjust_for_ambient_noise: bool = True
) -> BackgroundAudioRecorder:
    """
    Start a background task that continuously records audio and stores it in a queue.

    Args:
        max_phrase_duration (int, optional): The maximum duration of a phrase to record.
            Defaults to 5.
        adjust_for_ambient_noise (bool, optional): Adjust recognizer sensitivity to
            ambient noise. Defaults to True.

    Returns:
        BackgroundRecorder: The background recorder instance that is recording audio.

    Example:
        ```python
        import marvin.audio
        recorder = marvin.audio.record_background()
        for clip in recorder.stream():
            print(marvin.transcribe(clip))

            if some_condition:
                recorder.stop()
        ```
    """
    recorder = BackgroundAudioRecorder()
    recorder.start(
        max_phrase_duration=max_phrase_duration,
        adjust_for_ambient_noise=adjust_for_ambient_noise,
    )
    return recorder
