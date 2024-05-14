# Captioning images

Marvin can use OpenAI's vision API to process images as inputs. 

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>caption</code> function generates text from images.
  </p>
</div>



!!! example

    Generate a description of the following image, hypothetically available at `/path/to/marvin.png`:

    ![](/assets/images/docs/vision/marvin.png)

    
    ```python
    import marvin

    caption = marvin.caption(marvin.Image.from_path('/path/to/marvin.png'))
    ```

    !!! success "Result"
    
        "A cute, small robot with a square head and large, glowing eyes sits on a surface of wavy, colorful lines. The background is dark with scattered, glowing particles, creating a magical and futuristic atmosphere."
    

<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin passes your images to the OpenAI vision API as part of a larger prompt.
  </p>
</div>


## Providing instructions

The `instructions` parameter offers an additional layer of control, enabling more nuanced caption generation, especially in ambiguous or complex scenarios.

## Captions for multiple images

To generate a single caption for multiple images, pass a list of `Image` objects to `caption`:

```python
marvin.caption(
  [
    marvin.Image.from_path('/path/to/img1.png'),
    marvin.Image.from_path('/path/to/img2.png')
  ],
  instructions='...'
)
```


## Model parameters
You can pass parameters to the underlying API via the `model_kwargs` argument of `caption`. These parameters are passed directly to the API, so you can use any supported parameter.



## Async support

If you are using Marvin in an async environment, you can use `caption_async`:

```python
caption = await marvin.beta.caption_async(image=Path('/path/to/marvin.png'))
```
## Mapping

To generate individual captions for a list of inputs at once, use `.map`. Note that this is different than generating a single caption for multiple images, which is done by passing a list of `Image` objects to `caption`.

```python
inputs = [
    marvin.Image.from_path('/path/to/img1.png'),
    marvin.Image.from_path('/path/to/img2.png')
]
result = marvin.caption.map(inputs)
assert len(result) == 2
```

(`marvin.cast_async.map` is also available for async environments.)

Mapping automatically issues parallel requests to the API, making it a highly efficient way to work with multiple inputs at once. The result is a list of outputs in the same order as the inputs.