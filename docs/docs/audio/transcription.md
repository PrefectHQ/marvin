# Generating transcriptions

Marvin can generate text from speech. 

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>transcribe</code> function generates text from audio.
  </p>
</div>



!!! example

    Suppose you have the following audio saved as `fancy_computer.mp3`:

    <audio controls>
      <source src="/assets/audio/fancy_computer.mp3" type="audio/mpeg">
      Your browser does not support the audio element.
    </audio>

    To generate a transcription, provide the path to the file:

    ```python
    import marvin

    transcription = marvin.transcribe("fancy_computer.mp3")
    ```

    !!! success "Result"
        ```python
        assert transcription == "I sure like being inside this fancy computer."
        ```

        

<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin passes your file to the OpenAI transcription API, which returns an transcript.
  </p>
</div>

## Supported audio formats

You can provide audio data to `transcribe` in a variety of ways. Marvin supports the following encodings: flac, m4a, mp3, mp4, mpeg, mpga, oga, ogg, wav, and webm.

### Marvin `Audio` object

Marvin provides an `Audio` object that makes it easier to work with audio. Typically it is imported from the `marvin.audio` module, which requires the `audio` extra to be installed. If it isn't installed, you can still import the `Audio` object from `marvin.types`, though some additional functionality will not be available.

```python
from marvin.audio import Audio
# or, if the audio extra is not installed:
# from marvin.types import Audio

audio = Audio.from_path("fancy_computer.mp3")
transcription = marvin.transcribe(audio)
```


### Path to a local file

Provide a string or `Path` representing the path to a local audio file:

```python
marvin.transcribe("fancy_computer.mp3")
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
assert result == "I sure like being inside this fancy computer."
```



## Model parameters
You can pass parameters to the underlying API via the `model_kwargs` argument. These parameters are passed directly to the respective APIs, so you can use any supported parameter.
