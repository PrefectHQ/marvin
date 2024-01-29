# Hogwarts sorting hat

![](hogwarts_patch.webp){width="400"}


!!! example "What house am I?"
    ```python
    import marvin

    description = "Brave, daring, chivalrous, and sometimes a bit reckless."

    house = marvin.classify(
        description,
        labels=["Gryffindor", "Hufflepuff", "Ravenclaw", "Slytherin"]
    )
    ```

    !!! success "Welcome to Gryffindor!"
        ```python
        assert house == "Gryffindor"
        ```