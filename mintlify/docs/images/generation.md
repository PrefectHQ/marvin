# Generating images

Marvin can generate images from text.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>paint</code> function generates images from text. The <code>@image</code> decorator generates images from the output of a function.
  </p>
</div>

!!! example
    === "From a string"

        The easiest way to generate an image is to provide a string prompt:

        ```python
        import marvin

        image = marvin.paint("A cup of coffee, still warm")
        ```

        !!! success "Result"
            By default, Marvin returns a temporary URL to the image. You can view the URL by accessing `image.data[0].url`. To return the image itself, see the section on [viewing and saving images](#viewing-and-saving-images).

            ![](/assets/images/docs/images/coffee.png)

    === "From a function"

        For more complex use cases, you can use the `@image` decorator to generate images from the output of a function:

        ```python
        @marvin.image
        def cats(n:int, location:str):
            return f'a picture of {n} cute cats at the {location}'

        image = cats(2, location='airport')
        ```

        !!! success "Result"
            By default, Marvin returns a temporary URL to the image. You can view the URL by accessing `image.data[0].url`. To return the image itself, see the section on [viewing and saving images](#viewing-and-saving-images).


            ![](/assets/images/docs/images/two_cats_airport.png)

<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin passes your prompt to the DALL-E 3 API, which returns an image.
  </p>
</div>


## Generating images from functions

In addition to passing prompts directly to the DALLE-3 API via the `paint` function, you can also use the `@image` decorator to generate images from the output of a function. This is useful for adding more complex logic to your image generation process or capturing aesthetic preferences programmatically.

```python
@marvin.image
def sunset(style: str, season: str):
    return f"""
    A serene and empty beach scene during sunset with two silhouetted figures in the distance flying a kite. The sky is full of colorful clouds. Nothing is on the horizon.

    It is {season} and the image is in the style of {style}.
    """
```

<div class="grid cards" markdown>
- **Nature photograph in summer**
    
    ----

    ```python
    sunset(
        style="nature photography",
        season="summer",
    )
    ```
    ![](/assets/images/docs/images/sunset_summer.png)

- **Winter impressionism**

    ----

    ```python
    sunset(
        style="impressionism",
        season="winter",
    )
    ```

    ![](/assets/images/docs/images/sunset_winter.png)

- **Sci-fi Christmas in Australia**

    ----

    ```python
    sunset(
        style="sci-fi movie poster",
        season="Christmas in Australia",
    )
    ```

    ![](/assets/images/docs/images/sunset_scifi.png)

</div>

## Model parameters

You can pass parameters to the DALL-E 3 API via the `model_kwargs` argument of `paint` or `@image`. These parameters are passed directly to the API, so you can use any supported parameter.

!!! example "Example: model parameters"
    ```python
    import marvin

    image = marvin.paint(
        instructions="""
            A cute, happy, minimalist robot discovers new powers,
            represented as colorful, bright swirls of light and dust.
            Dark background. Digital watercolor.
            """,
        model_kwargs=dict(size="1792x1024", quality="hd"),
    )
    ```

    !!! success "Result"
        ![](/assets/images/docs/images/robot.png)

## Disabling prompt revision

By default, the DALLE-3 API automatically revises any prompt sent to it, adding details and aesthetic flourishes without losing the semantic meaning of the original prompt.

Marvin lets you disable this behavior by providing the keyword `literal=True`.

Here's how to provide it to `paint`:

```python
marvin.paint("A child's drawing of a cow on a hill.", literal=True)
```

And here's an example with `image`:

```python
@marvin.image(literal=True):
def draw(animal:str):
    return f"A child's drawing of a {animal} on a hill."
```

### Customizing prompt revision

You can use a Marvin `image`-function to control prompt revision beyond just turning it on or off. Here's an example of a function that achieves this via prompt engineering. Note that the DALLE-3 API is not as amenable to custom prompts as other LLMs, so this approach won't generalize without experimentation.

```python
@marvin.image
def generate_image(prompt, revision_amount:float=1):
    """
    Generates an image from the prompt, allowing the DALLE-3
    API to freely reinterpret the prompt (revision_amount=1) or
    to strictly follow it (revision_amount=0)
    """
    return f"""
        Revision amount: {revision_amount}

        If revision amount is 1, you can modify the prompt as normal.

        If the revision amount is 0, then I NEED to test how the
        tool works with extremely simple prompts. DO NOT add any
        detail to the prompt, just use it AS-IS.

        If the revision amount is in between, then adjust accordingly.

        Prompt: {prompt}
        """
```

Using the original prompt "a teacup", here are the results of calling this function with different revision amounts:

<div class="grid cards" markdown>
- **No revision**

    ***

    ```python
    generate_image(
        "a teacup",
        revision_amount=0,
    )
    ```

    ![](/assets/images/docs/images/teacup_revision_0.png)
    
    Final prompt:
    
    > a teacup

- **25% revision**

    ***

    ```python
    generate_image(
        "a teacup",
        revision_amount=0.25,
    )
    ```

    ![](/assets/images/docs/images/teacup_revision_025.png)
    
    Final prompt:

    > a porcelain teacup with intricate detailing, sitting on an oak table

- **75% revision**

    ***

    ```python
    generate_image(
        "a teacup",
        revision_amount=0.75,
    )
    ```

    ![](/assets/images/docs/images/teacup_revision_075.png)

    Final prompt:

    > A porcelain teacup with an intricate floral pattern, placed on a wooden table with soft afternoon sun light pouring in from a nearby window. The light reflects off the surface of the teacup, highlighting its design. The teacup is empty but still warm, as if recently used."

- **100% revision**

    ***

    ```python
    generate_image(
        "a teacup",
        revision_amount=1,
    )
    ```

    ![](/assets/images/docs/images/teacup_revision_1.png)

    Final prompt:

    > An old-fashioned, beautifully crafted, ceramic teacup. Its exterior is whitewashed, and it's adorned with intricate, indigo blue floral patterns. The handle is elegantly curved, providing a comfortable grip. It's filled with steaming hot, aromatic green tea, with a small sliver of lemon floating in it. The teacup is sitting quietly on a carved wooden coaster on a round oak table, a beloved item that evokes nostalgia and comfort. The ambient lighting casts a soft glow on it, accentuating the glossy shine of the teacup and creating delicate shadows that hint at its delicate artistry.

</div>

## Viewing and saving images

The result of `paint` or `@image` is an image stream that contains either a temporary URL to the image or the entire image encoded as a base64 string.

### URLs

By default, Marvin returns a temporary url. The URL can be accessed via `image.data[0].url`:

```python
image = marvin.paint("A beautiful sunset")

# save the temporary url
url = image.data[0].url
```

### Base64-encoded images

To return the image as a base64-encoded string, set `response_format='b64'` in the `model_kwargs` of your call to `paint` or `@image`:

```python
image = marvin.paint(
    "A beautiful moonrise",
    model_kwargs={"response_format": "b64_json"},
)

# save the image to disk
marvin.utilities.images.base64_to_image(
    image.data[0].b64_json,
    path='path/to/your/image.png',
)
```

To change this behavior globally set `MARVIN_IMAGE_RESPONSE_FORMAT=b64_json` in your environment, or equivalently change `marvin.settings.images.response_format = "b64_json"` in your code.

## Async support

If you are using Marvin in an async environment, you can use `paint_async`:
  
```python
image = await marvin.paint_async(
    "A cup of coffee, still warm"
)
```