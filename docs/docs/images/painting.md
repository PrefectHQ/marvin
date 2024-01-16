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

        marvin.paint('a picture of 3 cute cats')
        ```

        !!! success "Result"
            ![](/assets/images/docs/images/three_cats.png)
        
    === "From a function"

        For more complex use cases, you can use the `@image` decorator to generate images from the output of a function:
        
        ```python
        @marvin.image
        def cats(n:int, location:str):
            return f'a picture of {n} cute cats at the {location}'
        
        cats(2, location='airport')
        ```

        !!! success "Result"
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
    return f"A view of a sunset, in the style of {style}, during {season}"
```

<div class="grid cards" markdown>
- **Nature photograph in summer**
    
    ---

    ```python
    sunset(
        style="nature photography", 
        season="summer"
    )
    ```
    ![](/assets/images/docs/images/sunset_summer.png)

- **Winter impressionism**
    
    ---

    ```python
    sunset(
        style="impressionism", 
        season="winter"
    )
    ```
    ![](/assets/images/docs/images/sunset_winter.png)

- **Something else**
    
    ---

    ```python
    sunset(
        style="sci-fi movie poster", 
        season="Christmas in Australia"
    )
    ```
    ![](/assets/images/docs/images/sunset_scifi.png)
</div>

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

    ---
    ```python
    generate_image(
      "a teacup", 
      revision_amount=0
    )
    ```
    Final prompt:

    ![](/assets/images/docs/images/teacup_revision_0.png)
    > a teacup


- **25% revision**

    ---
    ```python
    generate_image(
      "a teacup", 
      revision_amount=0.25
    )
    ```
  
    ![](/assets/images/docs/images/teacup_revision_025.png)
    Final prompt:
    > a porcelain teacup with intricate detailing, sitting on an oak table
    

- **75% revision**

    ---
    ```python
    generate_image(
      "a teacup", 
      revision_amount=0.75
    )
    ```
  
    ![](/assets/images/docs/images/teacup_revision_075.png)

    Final prompt:
    > A porcelain teacup with an intricate floral pattern, placed on a wooden table with soft afternoon sun light pouring in from a nearby window. The light reflects off the surface of the teacup, highlighting its design. The teacup is empty but still warm, as if recently used."


- **100% revision**
  
    ---
    ```python
    generate_image(
      "a teacup", 
      revision_amount=1
    )
    ```
    ![](/assets/images/docs/images/teacup_revision_1.png)

    Final prompt:
    > An old-fashioned, beautifully crafted, ceramic teacup. Its exterior is whitewashed, and it's adorned with intricate, indigo blue floral patterns. The handle is elegantly curved, providing a comfortable grip. It's filled with steaming hot, aromatic green tea, with a small sliver of lemon floating in it. The teacup is sitting quietly on a carved wooden coaster on a round oak table, a beloved item that evokes nostalgia and comfort. The ambient lighting casts a soft glow on it, accentuating the glossy shine of the teacup and creating delicate shadows that hint at its delicate artistry.
    
</div>