# Classifying images

Marvin can use OpenAI's vision API to process images and classify them into categories.

!!! tip "Beta"
    Please note that vision support in Marvin is still in beta, as OpenAI has not finalized the vision API yet. While it works as expected, it is subject to change.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>classify_vision</code> function can classify images as one of many labels.
  </p>
</div>


<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    
  This involves a two-step process: first, a caption is generated for the image that is aligned with the structuring goal. Next, the actual classify operation is performed with an LLM.

  </p>
</div>



!!! example "Example"


    ![](https://upload.wikimedia.org/wikipedia/commons/d/d5/Retriever_in_water.jpg)

    
    ```python
    import marvin

    img = 'https://upload.wikimedia.org/wikipedia/commons/d/d5/Retriever_in_water.jpg'

    animal = marvin.classify_vision(
        img, 
        labels=['dog', 'cat', 'bird', 'fish', 'deer']
    )
    
    dry_or_wet = marvin.classify_vision(
        img, 
        labels=['dry', 'wet'], 
        instructions='Is the animal wet?'
    )
    ```

    !!! success "Result"
        ```python
        assert animal == 'dog'
        assert dry_or_wet == 'wet'
        ```
