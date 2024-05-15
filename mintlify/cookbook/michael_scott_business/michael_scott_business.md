# Michael Scott's four kinds of businesses

![](michael_scott.jpg)


!!! example "What kind of business are LLMs?"
    ```python
    import marvin

    businesses = [
        "tourism",
        "food service",
        "railroads",
        "sales",
        "hospitals/manufacturing",
        "air travel",
    ]

    result = marvin.classify("LLMs", labels=businesses)
    ```

    !!! success "Tourism"
        ```python
        assert result == "tourism"
        ```