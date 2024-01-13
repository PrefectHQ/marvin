# Extracting entities from images

Marvin can use OpenAI's vision API to process images and convert them into structured data, transforming unstructured information into native types that are appropriate for a variety of programmatic use cases.


!!! tip "Beta"
    Please note that vision support in Marvin is still in beta, as OpenAI has not finalized the vision API yet. While it works as expected, it is subject to change.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>extract_vision</code> function can extract entities from images.
  </p>
</div>


<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    
  This involves a two-step process: first, a caption is generated for the image that is aligned with the structuring goal. Next, the actual extract operation is performed with an LLM.

  </p>
</div>



!!! example "Example: Dog breeds"

    We will extract the breed of each dog in this image:

    ![](https://images.unsplash.com/photo-1548199973-03cce0bbc87b?q=80&w=2969&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D)

    
    ```python
    import marvin
    
    img = 'https://images.unsplash.com/photo-1548199973-03cce0bbc87b?q=80&w=2969&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'

    result = marvin.extract_vision(img, target=str, instructions='dog breeds')
    ```

    !!! success "Result"
        ```python
        assert result == ['Pembroke Welsh Corgi', 'Yorkshire Terrier']
        ```    



!!! example "Example: Identifying money"

    We will extract information about all of the bills in this image:

    ![](https://upload.wikimedia.org/wikipedia/commons/6/63/USCurrency_Federal_Reserve.jpg)

    
    ```python
    import marvin
    
    img = 'https://upload.wikimedia.org/wikipedia/commons/6/63/USCurrency_Federal_Reserve.jpg'
    
    values = marvin.extract_vision(img, target=int, instructions='Value of each of the bills')
    ```


    !!! success "Result"
        ```python
        assert values == [1, 1, 5, 10, 5]
        ```

