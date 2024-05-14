# Extracting entities from images

Marvin can use OpenAI's vision API to process images and convert them into structured data, transforming unstructured information into native types that are appropriate for a variety of programmatic use cases.



<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The beta <code>extract</code> function can extract entities from images and text.
  </p>
</div>


<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    
  This involves a two-step process: first, a caption is generated for the image that is aligned with the structuring goal. Next, the actual extract operation is performed with an LLM.

  </p>
</div>



!!! example "Example: identifying dogs"

    We will extract the breed of each dog in this image:

    ![](https://images.unsplash.com/photo-1548199973-03cce0bbc87b?)

    
    ```python
    import marvin
    
    img = marvin.Image(
        "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?",
    )

    result = marvin.extract(img, target=str, instructions="dog breeds")
    ```

    !!! success "Result"
        ```python
        result == ["Pembroke Welsh Corgi", "Yorkshire Terrier"]
        ```    

## Model parameters
You can pass parameters to the underlying API via the `model_kwargs` argument of `extract`. These parameters are passed directly to the API, so you can use any supported parameter.


## Async support
If you are using Marvin in an async environment, you can use `extract_async`:
  
```python
result = await marvin.extract_async(
    "I drove from New York to California.",
    target=str,
    instructions="2-letter state codes",
) 

assert result == ["NY", "CA"]
```

## Mapping

To extract from a list of inputs at once, use `.map`:

```python
inputs = [
    "I drove from New York to California.",
    "I took a flight from NYC to BOS."
]
result = marvin.extract.map(inputs, target=str, instructions="2-letter state codes")
assert result  == [["NY", "CA"], ["NY", "MA"]]
```

(`marvin.extract_async.map` is also available for async environments.)

Mapping automatically issues parallel requests to the API, making it a highly efficient way to work with multiple inputs at once. The result is a list of outputs in the same order as the inputs.