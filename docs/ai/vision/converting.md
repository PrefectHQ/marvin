# Converting images to data

Marvin can use OpenAI's vision API to process images and convert them into structured data, transforming unstructured information into native types that are appropriate for a variety of programmatic use cases.





!!! tip "Beta"
    Please note that vision support in Marvin is still in beta, as OpenAI has not finalized the vision API yet. While it works as expected, it is subject to change.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>cast_vision</code> function can cast images to structured types.
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

    ![](https://upload.wikimedia.org/wikipedia/commons/7/7a/View_of_Empire_State_Building_from_Rockefeller_Center_New_York_City_dllu_%28cropped%29.jpg)

    
    ```python
    import marvin
    from pydantic import BaseModel

    class Location(BaseModel):
        city: str
        state: str
    
    img = 'https://upload.wikimedia.org/wikipedia/commons/7/7a/View_of_Empire_State_Building_from_Rockefeller_Center_New_York_City_dllu_%28cropped%29.jpg'
    result = marvin.cast_vision(img, target=Location)
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
    
    img = 'https://hastie.su.domains/ElemStatLearn/CoverII_small.jpg'
    result = marvin.cast_vision(img, target=Book)
    ```

    !!! success "Result"
        ```python
        assert result == Book(
            title='The Elements of Statistical Learning', 
            subtitle='Data Mining, Inference, and Prediction', 
            authors=['Trevor Hastie', 'Robert Tibshirani', 'Jerome Friedman']
        )
        ```    
