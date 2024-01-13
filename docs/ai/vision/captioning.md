# Generating images

Marvin can use OpenAI's vision API to process images as inputs. 

!!! tip "Beta"
    Please note that vision support in Marvin is still in beta, as OpenAI has not finalized the vision API yet. While it works as expected, it is subject to change.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>caption</code> function generates text from images.
  </p>
</div>



!!! example

    Generate a description of the following image, hypothetically available at `/path/to/marvin.jpg`:

    ![](/assets/images/core/vision/marvin.webp)

    
    ```python
    import marvin
    from pathlib import Path

    marvin.beta.caption(image=Path('/path/to/marvin.jpg'))
    ```

    !!! success "Result"
        "This is a digital illustration featuring a stylized, cute character resembling a Funko Pop vinyl figure with large, shiny eyes and a square-shaped head, sitting on abstract wavy shapes that simulate a landscape. The whimsical figure is set against a dark background with sparkling, colorful bokeh effects, giving it a magical, dreamy atmosphere."
    

<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin passes your images to the OpenAI vision API as part of a larger prompt.
  </p>
</div>

