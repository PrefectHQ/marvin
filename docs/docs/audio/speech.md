# Generating speech

Marvin can generate speech from text. 

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>speak</code> function generates audio from text. The <code>@speech</code> decorator generates speech from the output of a function.
  </p>
</div>



!!! example
    === "From a string"

        The easiest way to generate speech is to provide a string:
        
        ```python
        import marvin

        audio = marvin.speak("I sure like being inside this fancy computer!")
        ```

        !!! success "Result"
            ```python
            audio.play("fancy_computer.mp3")
            ```
            <audio controls>
              <source src="/assets/audio/fancy_computer.mp3" type="audio/mpeg">
              Your browser does not support the audio element.
            </audio>

        
    === "From a function"

        For more complex use cases, you can use the `@image` decorator to generate images from the output of a function:
        
        ```python
        @marvin.speech
        def say_hello(name: str):
            return f'Hello, {name}! How are you doing today?'
        

        audio = say_hello("Arthur")
        ```

        !!! success "Result"
            ```python
            audio.play("hello_arthur.mp3")
            ```
            <audio controls>
              <source src="/assets/audio/hello_arthur.mp3" type="audio/mpeg">
              Your browser does not support the audio element.
            </audio>

<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin passes your prompt to the OpenAI speech API, which returns an audio file.
  </p>
</div>

!!! tip "Text is generated verbatim"

    Unlike the images API, OpenAI's speech API does not modify or revise your input prompt in any way. Whatever text you provide is exactly what will be spoken. 

    Therefore, you can use the `speak` function to generate speech from any string, or use the `@speech` decorator to generate speech from the string output of any function.




## Generating speech
By default, OpenAI generates speech from the text you provide, verbatim. We can use Marvin functions to generate more interesting speech by modifying the prompt before passing it to the speech API. For example, we can use a function to generate a line of dialogue that reflects a specific intent. And because of Marvin's modular design, we can simply add a `@speech` decorator to the function to generate speech from its output.

```python
import marvin

@marvin.speech
@marvin.fn
def ai_say(intent: str) -> str:
    '''
    Given an `intent`, generate a line of diagogue that 
    reflects the intent / tone / instruction without repeating 
    it verbatim.
    '''
    
ai_say('hello') 
# Hi there! Nice to meet you.
```

!!! success "Result"
    <audio controls>
      <source src="/assets/audio/ai_say.mp3" type="audio/mpeg">
      Your browser does not support the audio element.
    </audio>

### Playing audio

The result of `speak` and `@speech` is an `Audio` object that can be played by calling its `play` method. By default, playback will start as soon as the first bytes of audio are available. See the note on [streaming audio](#streaming-audio) for more information.

```python
audio = marvin.speak("Hello, world!")
audio.play()
```

#### Streaming audio
By default, Marvin streams audio from the OpenAI API, which means that playback can start as soon as the first bytes of audio are available. This can be useful for long audio files, as it allows you to start listening to the audio before it has finished generating. If you want to wait for the entire audio file to be generated before starting playback, you can pass `stream=False`:

```python
audio = marvin.speak("Hello, world!", stream=False)
```
Note that streaming is only supported with the `pcm` (or raw) audio file format, and an error will be raised if you try to generate speech in a different format with `stream=True`. However, you can always save `pcm` audio to a file in a different format after it has been generated.

### Saving audio
To save an `Audio` object to a file, you can call its `save` method:

```python
audio = marvin.speak("Hello, world!")
audio.save("hello_world.mp3")
```

Marvin will attempt to infer the correct file format from the file extension you provide. If you want to save the audio in a different format, you can pass a `format` argument to `save`.

### Saving audio


## Choosing a voice

Both `speak` and `@speech` accept a `voice` parameter that allows you to choose from a variety of voices. You can preview the available voices [here](https://platform.openai.com/docs/guides/text-to-speech/voice-options).

```python
The result of the `speak` function and `@speech` decorator is an audio stream.

audio = marvin.speak("Hello, world!", voice="nova")
audio.play("hello_world.mp3") 
```


## Model parameters
You can pass parameters to the underlying API via the `model_kwargs` arguments of `speak` and `@speech`. These parameters are passed directly to the respective APIs, so you can use any supported parameter.


## Async support

If you are using Marvin in an async environment, you can use `speak_async` (or decorate an async function with `@speech`) to generate speech asynchronously:

```python
result = await marvin.speak_async('I sure like being inside this fancy computer!')
```
