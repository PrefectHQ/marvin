# Converting images to data

Marvin can use OpenAI's vision API to process images and convert them into structured data, transforming unstructured information into native types that are appropriate for a variety of programmatic use cases.

The `marvin.beta.cast` function is an enhanced version of `marvin.cast` that accepts images as well as text.

!!! tip "Beta"
    Please note that vision support in Marvin is still in beta, as OpenAI has not finalized the vision API yet. While it works as expected, it is subject to change.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>cast</code> function can cast images to structured types.
  </p>
</div>

<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    
  This involves a two-step process: first, a caption is generated for the image that is aligned with the structuring goal. Next, the actual cast operation is performed with an LLM.

  </p>
</div>


!!! example "Example: locations"

    We will cast this image to a `Location` type:

    ![](https://images.unsplash.com/photo-1568515387631-8b650bbcdb90)


    ```python
    import marvin
    from pydantic import BaseModel, Field


    class Location(BaseModel):
        city: str
        state: str = Field(description="2-letter state abbreviation")


    img = marvin.beta.Image(
        "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90",
    )
    result = marvin.beta.cast(img, target=Location)
    ```

    !!! success "Result"
        ```python
        assert result == Location(city="New York", state="NY")
        ```

!!! example "Example: getting information about a book"

    We will cast this image to a `Book` to extract key information:

    ![](https://hastie.su.domains/ElemStatLearn/CoverII_small.jpg){ width="250" }


    ```python
    import marvin
    from pydantic import BaseModel


    class Book(BaseModel):
        title: str
        subtitle: str
        authors: list[str]


    img = marvin.beta.Image(
        "https://hastie.su.domains/ElemStatLearn/CoverII_small.jpg",
    )
    result = marvin.beta.cast(img, target=Book)
    ```

    !!! success "Result"
        ```python
        assert result == Book(
            title='The Elements of Statistical Learning',
            subtitle='Data Mining, Inference, and Prediction',
            authors=['Trevor Hastie', 'Robert Tibshirani', 'Jerome Friedman']
        )
        ```

## Instructions

If the target type isn't self-documenting, or you want to provide additional guidance, you can provide natural language `instructions` when calling `cast` in order to steer the output. 


!!! example "Example: checking groceries"

    Let's use this image to see if we got everything on our shopping list:

    ![](https://images.unsplash.com/photo-1588964895597-cfccd6e2dbf9)

    ```python
    import marvin

    shopping_list = ["bagels", "cabbage", "eggs", "apples", "oranges"]
    
    missing_items = marvin.beta.cast(
        marvin.beta.Image("https://images.unsplash.com/photo-1588964895597-cfccd6e2dbf9"), 
        target=list[str], 
        instructions=f"Did I forget anything on my list: {shopping_list}?",
    )

    ```

    !!! success "Result"
        ```python
        assert missing_items == ["eggs", "oranges"]
        ```

## Model parameters
You can pass parameters to the underlying API via the `model_kwargs` and `vision_model_kwargs` arguments of `cast`. These parameters are passed directly to the respective APIs, so you can use any supported parameter.

## Async support
If you are using `marvin` in an async environment, you can use `cast_async`:

```python
result = await marvin.beta.cast_async("one", int) 

assert result == 1
```

## Mapping

To transform a list of inputs at once, use `.map`:

```python
inputs = [
    "I bought two donuts.",
    "I bought six hot dogs."
]
result = marvin.beta.cast.map(inputs, int)
assert result  == [2, 6]
```

(`marvin.beta.cast_async.map` is also available for async environments.)

Mapping automatically issues parallel requests to the API, making it a highly efficient way to work with multiple inputs at once. The result is a list of outputs in the same order as the inputs.