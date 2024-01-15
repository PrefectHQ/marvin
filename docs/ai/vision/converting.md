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




!!! example "Example: Locations"

    We will cast this image to a `Location` type:

    ![](https://images.unsplash.com/photo-1568515387631-8b650bbcdb90)

    
    ```python
    import marvin
    from pydantic import BaseModel, Field

    class Location(BaseModel):
        city: str
        state: str = Field(description="2-letter state abbreviation")
    
    img = marvin.beta.Image('https://images.unsplash.com/photo-1568515387631-8b650bbcdb90')
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
    
    img = marvin.beta.Image('https://hastie.su.domains/ElemStatLearn/CoverII_small.jpg')
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
