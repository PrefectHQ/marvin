# Classifying images

Marvin can use OpenAI's vision API to process images and classify them into categories.

The `marvin.beta.classify` function is an enhanced version of `marvin.classify` that accepts images as well as text. 

!!! tip "Beta"
    Please note that vision support in Marvin is still in beta, as OpenAI has not finalized the vision API yet. While it works as expected, it is subject to change.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>classify</code> function can classify images as one of many labels.
  </p>
</div>


<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    
  This involves a two-step process: first, a caption is generated for the image that is aligned with the structuring goal. Next, the actual classify operation is performed with an LLM.

  </p>
</div>



!!! example "Example"

    We will classify the animal in this image, as well as whether it is wet or dry:

    ![](https://upload.wikimedia.org/wikipedia/commons/d/d5/Retriever_in_water.jpg)

    
    ```python
    import marvin

    img = marvin.beta.Image('https://upload.wikimedia.org/wikipedia/commons/d/d5/Retriever_in_water.jpg')

    animal = marvin.beta.classify(
        img, 
        labels=['dog', 'cat', 'bird', 'fish', 'deer']
    )
    
    dry_or_wet = marvin.beta.classify(
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
