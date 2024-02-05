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


## Async support

If you are using Marvin in an async environment, you can use `transcribe_async`:

```python
result = await marvin.transcribe_async('fancy_computer.mp3')
assert result.text == "I sure like being inside this fancy computer."
```



## Model parameters
You can pass parameters to the underlying API via the `model_kwargs` argument. These parameters are passed directly to the respective APIs, so you can use any supported parameter.