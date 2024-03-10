# Recording audio

Marvin has utilities for working with audio data beyond generating speech and transcription. To use these utilities, you must install Marvin with the `audio` extra:

```bash
pip install marvin[audio]
```

## Audio objects

The `Audio` object gives users a simple way to work with audio data that is compatible with all of Marvin's audio abilities. You can create an `Audio` object from a file path or by providing audio bytes directly.


### From a file path
```python
from marvin.audio import Audio
audio = Audio.from_path("fancy_computer.mp3")
```
### From data
```python
audio = Audio(data=audio_bytes)
```

### Playing audio
You can play audio from an `Audio` object using the `play` method:

```python
audio.play()
```

## Recording audio

Marvin can record audio from your computer's microphone. There are a variety of options for recording audio in order to match your specific use case. 



### Recording for a set duration

The basic `record` function records audio for a specified duration. The duration is provided in seconds.

```python
import marvin.audio

# record 5 seconds of audio
audio = marvin.audio.record(duration=5)
audio.play()
```

### Recording a phrase

The `record_phrase` function records audio until a pause is detected. This is useful for recording a phrase or sentence.

```python
import marvin.audio

audio = marvin.audio.record_phrase()
audio.play()
```

There are a few keyword arguments that can be used to customize the behavior of `record_phrase`:
- `after_phrase_silence`: The duration of silence to consider the end of a phrase. The default is 0.8 seconds.
- `timeout`: The maximum time to wait for speech to start before giving up. The default is no timeout.
- `max_phrase_duration`: The maximum duration for recording a phrase. The default is no limit.
- `adjust_for_ambient_noise`: Whether to adjust the recognizer sensitivity to ambient noise before starting recording. The default is `True`, but note that this introduces a minor latency between the time the function is called and the time recording starts. A log message will be printed to indicate when the calibration is complete.

### Recording continuously

The `record_background` function records audio continuously in the background. This is useful for recording audio while doing other tasks or processing audio in real time.

The result of `record_background` is a `BackgroundAudioRecorder` object, which can be used to control the recording (including stopping it) and to access the recorded audio as a stream.

By default, the audio is recorded as a series of phrases, meaning a new `Audio` object is created each time a phase is detected. Audio objects are queued and can be accessed by iterating over the recorder's `stream` method.

```python
import marvin
import marvin.audio

recorder = marvin.audio.record_background()

counter = 0
for audio in recorder.stream():
    counter += 1
    # process each audio phrase
    marvin.transcribe(audio)

    # stop recording
    if counter == 3:
        recorder.stop()
```