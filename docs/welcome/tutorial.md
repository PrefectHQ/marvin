---
toc_depth: 3
---
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

## Working with text

Marvin has a variety of tools that let you use LLMs to solve common but complex problems. In this tutorial, we'll try out a few of them to get a feel for how Marvin works. By the end of the tutorial, you'll have tried some of Marvin's advanced features and be ready to take on the universe! Just don't forget your towel.

### 🏷️ Classification

Classification is one of Marvin's most straightforward features. Given some text and a list of labels, Marvin will choose the label that best fits the text. The `classify` function is great for tasks like sentiment analysis, intent classification, routing, and more.


!!! Example "First steps: true/false"

    Here is the simplest possible classification example, mapping the word "yes" to the boolean values `True` or `False`:

    ```python
    import marvin

    result = marvin.classify("yes", labels=bool)
    ```

    !!! success "Result"
        ```python
        assert result is True
        ```


!!! Example "A more practical example: sentiment"
    
    A more useful example is to classify text as one of several categories, provided as a list of labels. In this example, we build a basic sentiment classifier for any text:

    ```python
    import marvin

    result = marvin.classify(
        "Marvin is so easy to use!",
        labels=["positive", "negative", "meh"],
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

!!! Example "Feature extraction"

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

!!! Example "Location extraction"

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
    
### ✨ Generation

So far, we've used Marvin to take existing text and convert it to a more structured or modified form that preserves its content but makes it easier to work with. Marvin can also generate synthetic data from a schema or instructions. This is incredibly useful for ideation, testing, data augmentation, populating databases, and more.

Let's use Marvin's `generate` function to produce synthetic data. The `generate` function takes either a target type or natural language instructions (or both), as well as the number of items to generate, and returns a list of synthetic data that complies with the instructions.

!!! Example "Locations named after presidents"

    Earlier, we extracted locations from text. Now, let's generate some new locations:

    ```python
    import marvin
    from pydantic import BaseModel

    class Location(BaseModel):
        city: str
        state: str

    locations = marvin.generate(
        n=4,
        target=Location,
        instructions="US cities named after presidents",
    )
    ```

    !!! success "Result"
        (Note: your results may vary)

        ```python
        locations == [
            Location(city="Washington", state="DC"),
            Location(city="Jackson", state="MS"),
            Location(city="Lincoln", state="NE"),
            Location(city="Cleveland", state="OH"),
        ]
        ```


In addition to structured types, Marvin can generate new text from instructions.

!!! Example "Character names"

    Let's generate some character names for a role-playing game:

    ```python
    import marvin

    names = marvin.generate(
        n=5,
        instructions="Character names for a fantasy RPG",
    )
    ```

    !!! success "Result"
        (Note: your results may vary)

        ```python
        names = [
            "Aelar Galanodel",
            "Draka Steelshadow",
            "Elyndra Silvershade",
            "Brom Ironfist",
            "Thalia Windwhisper"
        ]
        ```

### 🦾 AI Functions

Now you've seen Marvin's most common tools. But what if you want to do something more custom? That's where AI functions come in. AI functions let you combine any inputs, instructions, and output types to create custom AI-powered behaviors.

Marvin functions *look* just like regular Python functions, but notice that they don't have any source code. When you call these functions, the outputs are generated by an LLM on-demand. This means they can handle really complex tasks that even an LLM wouldn't know how to generate code for.

!!! Example "Sentiment analysis"

    Let's build a sentiment analysis function that takes text and returns a sentiment score. Normally, this would require a complex model and a lot of training data. But with Marvin, we only have to write the **form** of the function, and the AI takes care of the rest:

    ```python
    import marvin

    @marvin.fn
    def sentiment(text: str) -> float:
        """
        Returns a sentiment score for `text` on a 
        scale of -1.0 (negative) to 1.0 (positive)
        """
    ```

    !!! success "Result"

        Call the function to see its result:

        ```python
        sentiment("I love Marvin!") # 0.8
        sentiment("This example could use some work...") # -0.2
        ```

Marvin's AI functions are especially useful when you want to map a complex set of inputs to an output, usually involving some kind of natural language processing. For typed transformations or data generation, you may prefer to use a different Marvin tool, which have the real advantage of not looking "odd" to other Python developers. But for full control and conditional behaviors, AI functions are the way to go.

## Working with images

Marvin is multi-modal! In addition to text, Marvin can also work with images. Most of Marvin's image and vision support is beta because it relies on the GPT-4 vision model, which is still in preview. But you wouldn't be here if you didn't love cutting-edge technology, right?

### 🎨 Generation

Marvin gives you easy access to the DALL-E 3 image generation model. This model can generate images from text descriptions

!!! Example "Generating images"

    ```python
    marvin.paint("a simple cup of coffee, still warm")
    ```

    !!! success "Result"

        ![](assets/images/docs/images/coffee.png)

### 📝 Captioning

If you've already got an image, you can convert it to text using the `caption` function. Note the use of Marvin's `Image` type, which accepts either a local path to an image or a URL.

!!! Example "Captioning images"

    ```python
    import marvin


    caption = marvin.beta.caption(marvin.beta.Image("path/to/coffee.png"))
    ```

    !!! success "Result"

        (Note: your results may vary)

        ```python
        caption == """
            A ceramic cup of hot beverage with steam rising 
            from it, on a rustic wooden surface, backlit by 
            soft light coming in through a window.
            """
        ```

### 🚀  Transforming, classifying, and extracting

Now that you've seen that Marvin can turn images into text, you're probably wondering if we can use that text with the `cast`, `extract`, and `classify` functions we saw earlier. The answer is yes -- but we can do even better. 

If you caption an image, the resulting text might not capture the details that are most relevant to the text processing task you want to perform. For example, if you want to classify the breed of dog in an image, you're going to need very specific information that a generic caption might not provide.

Therefore, Marvin has beta versions of `cast`, `extract`, and `classify` that accept images as inputs. Instead of generating generic captions, these functions process the image in a way that is most conducive to the task at hand.

These functions are available under `marvin.beta` and work identically to their text-only counterparts except that they can take images as well as text inputs.


!!! example "Identifying dog breeds in an image"

    Let's identify the breed of each dog in this image by using the beta `extract` function.

    ![](https://images.unsplash.com/photo-1548199973-03cce0bbc87b?q=80&w=2969&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D)

    
    ```python
    import marvin
    
    img = marvin.beta.Image('https://images.unsplash.com/photo-1548199973-03cce0bbc87b?q=80&w=2969&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D')

    result = marvin.beta.extract(img, target=str, instructions='dog breeds')
    ```

    !!! success "Result"
        ```python
        result == ['Pembroke Welsh Corgi', 'Yorkshire Terrier']
        ```    

## Grab your towel

We hope this tutorial has given you a taste of what Marvin can do. There's a lot more to explore, including tools for interactive use cases (like chatbots and applications), audio generation, and more. 

To learn more, please explore the docs or say hi in our [Discord community](https://discord.gg/Kgw4HpcuYG)!

And remember:

!!! Example "Don't panic!"
    ```python
    import marvin

    audio = marvin.speak("and above all else... don't panic!")
    audio.stream_to_file("dont_panic.mp3")
    ```

    !!! success "Result"
        <audio controls>
            <source src="/assets/audio/dont_panic.mp3" type="audio/mpeg">
            Your browser does not support the audio element.
        </audio>