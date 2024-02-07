# Generating transcriptions

Marvin can generate text from speech. 

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>transcribe</code> function generates text from audio.
  </p>
</div>



!!! example

    <audio controls>
      <source src="/assets/audio/fancy_computer.mp3" type="audio/mpeg">
      Your browser does not support the audio element.
    </audio>

    To generate a transcription, provide the path to an audio file:

    ```python
    import marvin

    transcription = marvin.transcribe("fancy_computer.mp3")
    ```

    !!! success "Result"
        ```python
        assert transcription.text == "I sure like being inside this fancy computer."
        ```

        

<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin passes your file to the OpenAI transcription API, which returns an transcript.
  </p>
</div>

## Audio formats

Marvin supports the following audio formats: flac, m4a, mp3, mp4, mpeg, mpga, oga, ogg, wav, and webm.

You can provide audio data to `transcribe` as any of the following:

### Path to a local file

Provide a string or `Path` representing the path to a local audio file:

```python
from pathlib import Path

marvin.transcribe(Path("/path/to/audio.mp3"))
```

### File reference

Provide the audio data as an in-memory file object:

```python
with open("/path/to/audio.mp3", "rb") as f:
    marvin.transcribe(f)
```


### Raw bytes

Provide the audio data as raw bytes:

```python
marvin.transcribe(audio_bytes)
```

Note that the OpenAI transcription API requires a filename, so Marvin will supply `audio.mp3` if  you pass raw bytes. In practice, this doesn't appear to make a difference even if your audio is not an mp3 file (e.g. a wav file).


## Async support

If you are using Marvin in an async environment, you can use `transcribe_async`:

```python
result = await marvin.transcribe_async('fancy_computer.mp3')
assert result.text == "I sure like being inside this fancy computer."
```



## Model parameters
You can pass parameters to the underlying API via the `model_kwargs` argument. These parameters are passed directly to the respective APIs, so you can use any supported parameter.

## Live transcriptions

Marvin has experimental support for live transcriptions. This feature is subject to change.

!!! tip "requires pyaudio"
    Live transcriptions require the `pyaudio` package. You can install it with `pip install 'marvin[audio]', which
    (on MacOS at least) requires an installation of `portaudio` via `brew install portaudio`.

To start a live transcription, call `transcribe_live`. This will start recording audio from your microphone and periodically call a provided `callback` function with the latest transcription. If no callback is provided, it will print the transcription to the screen. 

The result of `transcribe_live` is a function that you can call to stop the transcription.



```python
stop_fn = marvin.audio.transcribe_live(callback=None)
# talk into your microphone
# ...
# ...
# call the stop function to stop recording
stop_fn()
```

