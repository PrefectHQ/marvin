# Tutorial

![](/docs/assets/images/heroes/dont_panic.png){ width=500 }

## Installing Marvin

Before we can start, you'll need to [install Marvin](installation.md). Come back here when you're done!

(Spoiler alert: run `pip install marvin -U`.)

## Getting an OpenAI API Key

Marvin uses OpenAI models to power all of its tools. In order to use Marvin, you'll need an OpenAI API key.

You can create an API key [on the OpenAI platform ](https://platform.openai.com/api-keys). Once you've created it, set it as an environment variable called `OPENAI_API_KEY` (for any application on your machine to use) or `MARVIN_OPENAI_API_KEY` (if you only want Marvin to use it). In addition to setting it in your terminal, you can also write the variable to a dotenv file at `~/.marvin/.env`.

For quick use, you can also pass your API key directly to Marvin at runtime. We do **NOT** recommend this for production:

```python
import marvin
marvin.settings.openai.api_key = 'YOUR_API_KEY'
```

## Tools

Marvin has a variety of tools that let you use LLMs to solve common but complex problems. In this tutorial, we'll try out a few of them to get a feel for how Marvin works. By the end of the tutorial, you'll have tried some of Marvin's advanced features and be ready to take on the universe! Just don't forget your towel.

### 🏷️ Classification

Classification is one of Marvin's most straightforward features. Given some text and a list of labels, Marvin will choose the label that best fits the text. The `classify` function is great for tasks like sentiment analysis, intent classification, routing, and more.

!!! Example "True/False"
    The simplest possible classification example maps the word "yes" to a boolean value like `True` or `False`:

    ```python
    import marvin

    result = marvin.classify("yes", labels=bool)
    ```

    !!! success "Result"
        ```python
        assert result is True
        ```

Now that you've seen the most basic example, let's try something a little more useful:

!!! Example "Sentiment"

    This example performs a basic sentiment analysis on some text:

    ```python
    import marvin

    result = marvin.classify(
        "Marvin is so easy to use!",
        labels=["positive", "negative"],
    )
    ```

    !!! success "Result"
        ```python
        assert result == "positive"
        ```

This is a great example of how all Marvin tools should feel. Historically, classifying text was a major challenge for natural language processing frameworks. But with Marvin, it's as easy as calling a function.

!!! tip "Structured labels"
    For the `classify` function, you can supply labels as a `list` of labels, a `bool` type, an `Enum` class, or a `Literal` type. This gives you many options for returning structured (non-string) labels.

### 🪄 Transformation

Classification maps text to a single label, but what if you want to convert text to a more structured form? Marvin's `cast` function lets you do just that. Given some text and a target type, Marvin will return a structured representation of the text.


!!! example "Standardization"

    Suppose you ran a survey and one of the questions asked where people live. Marvin can convert their freeform responses to a structured `Location` type:

    ```python
    import marvin
    from pydantic import BaseModel

    class Location(BaseModel):
        city: str
        state: str

    location = marvin.cast("NYC", target=Location)
    ```

    !!! success "Result"
        The string "NYC" was converted to a full `Location` object:

        ```python
        assert location == Location(city="New York", state="New York")
        ```

#### Instructions

All Marvin functions have an `instructions` parameter that let you fine-tune their behavior with natural language. For example, you can use instructions to tell Marvin to extract a specific type of information from a text or to format a response in a specific way.

Suppose you wanted to standardize the survey responses in the previous example, but instead of using a full Pydantic model, you wanted the result to still be a string. The `cast` function will accept `target=str`, but that's so general it's unlikely to do what you want without additional guidance. That's where instructions come in:

!!! example "Instructions"

    Repeat the previous example, but cast to a string according to the instructions:

    ```python
    import marvin

    location = marvin.cast(
        "NYC", 
        target=str, 
        instructions="Return the proper city and state name",
    )
    ```

    !!! success "Result"
        The result is a string that complies with the instructions:

        ```python
        assert location == "New York, New York"
        ```

### 🔍 Extraction

The `extract` function is like a generalization of the `cast` function: instead of transforming the entire text to a single target type, it extracts a list of entities from the text. This is useful for identifying people, places, ratings, keywords, and more.

!!! Example "Extraction"

    Suppose you wanted to extract the product features mentioned in a review:

    ```python
    import marvin

    features = marvin.extract(
        "I love my new phone's camera, but the battery life could be improved.",
        instructions="extract product features",
    )
    ```

    !!! success "Result"
        ```python
        assert features == ["camera", "battery life"]
        ```

The `extract` function can take a target type, just like `cast`. This lets you extract structured entities from text. For example, you could extract a list of `Location` objects from a text:

!!! Example "Extract locations"

    ```python
    import marvin
    from pydantic import BaseModel

    class Location(BaseModel):
        city: str
        state: str

    locations = marvin.extract(
        "They've got a game in NY, then they go to DC before Los Angeles.",
        target=Location
    )
    ```

    !!! success "Result"
        ```python
        assert locations == [
            Location(city="New York", state="New York"),
            Location(city="Washington", state="District of Columbia"),
            Location(city="Los Angeles", state="California"),
        ]
        ```
    