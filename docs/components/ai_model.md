AI Models are a high-level component, or building block, of Marvin. Like all Marvin components, they are completely standalone: you're free to use them with or without the rest of Marvin.

!!! abstract "What it does"
    A decorator that lets you extract structured data from unstructured text, documents, or instructions.


!!! example "Example"
    ```python
    from marvin import ai_model
    from pydantic import BaseModel, Field


    @ai_model
    class Location(BaseModel):
        city: str
        state: str = Field(..., description="The two-letter state abbreviation")

    # We can now put pass unstructured context to this model.
    Location("The Big Apple")
    ```
    
    ???+ Returns
        ```python
        Location(city='New York', state='NY')
        ```

!!! info "How it works"
    AI Models use an LLM to extract, infer, or deduce data from the provided text. The data is parsed with Pydantic into the provided schema.

!!! tip "When to use"
    - Best for extractive tasks: structuing of text or data models.
    - Best for writing NLP pipelines that would otherwise be impossible to create.
    - Good for model generation, though, see AI Function.

## Creating an AI Model

AI Models are identical to Pydantic `BaseModels`, except that they can attempt to parse natural language to populate their fields. To build an effective AI Model, be as specific as possible with your field names, field descriptions, docstring, and instructions.

To build a minimal AI model, decorate any standard Pydantic model, like this:

!!! example "Example"
    ```python
    from marvin import ai_model
    from pydantic import BaseModel, Field


    @ai_model
    class Location(BaseModel):
        """A representation of a US city and state"""

        city: str = Field(description="The city's proper name")
        state: str = Field(description="The state's two-letter abbreviation (e.g. NY)")

    # We can now put pass unstructured context to this model.
    Location("The Big Apple")
    ```
    
    ???+ Returns
        ```python
        Location(city='New York', state='NY')
        ```

## Configuring an AI Model

In addition to how you define the AI model itself, there are two ways to control its behavior at runtime: `instructions` and `model`.

### Providing instructions
When parsing text, AI Models can take up to three different forms of instruction:
- the AI Model's docstring (set at the class level)
- instructions passed to the `@ai_model` decorator (set at the class level)
- instructions passed to the AI Model when instantiated (set at the instance / call level)

The AI Model's docstring and the `@ai_model` instructions are roughly equivalent: they are both provided when the class is defined, not when it is instantiated, and are therefore applied to every instance of the class. Users can choose to put information in either location. If you only want to use one, our recommendation is to use the docstring for clarity. Alternatively, you may prefer to put the model's documentation in the docstring (as you would for a normal Pydantic model) and put parsing instructions in the `@ai_model` decorator, since those are unique to the LLM. This is entirely a matter of preference and users should opt for whichever is more clear; both the docstring and the `@ai_model` instructions are provided to the LLM in the same way.

Here is an example of an AI model with a documentation docstring and parsing instructions provided to the decorator:

!!! example "Example"
    ```python
    @ai_model(instructions="Translate to French")
    class Translation(BaseModel):
        """A record of original text and translated text"""

        original_text: str
        translated_text: str


    Translation("Hello, world!")
    ```

    ???+ Returns
        ```python
        Translation(original_text='Hello, world!', translated_text='Bonjour le monde!')
        ```

In the above case, we could have also put "translate to French" in the docstring (and perhaps renamed the object `FrenchTranslation`, since that's the only language it can represent).

The third opportunity to provide instructions is when the model is actually instantiated. These instructions are **combined** with any other instructions to guide the model behavior. Here's how we could use the same `Translation` object to handle multiple languages:

!!! example "Example"
    ```python
    @ai_model
    class Translation(BaseModel):
        """A record of original text and translated text"""

        original_text: str
        translated_text: str


    print(Translation("Hello, world!", instructions_="Translate to French"))
    print(Translation("Hello, world!", instructions_="Translate to German"))
    ```

    ???+ Returns
        ```python
        original_text='Hello, world!' translated_text='Bonjour, le monde!'
        original_text='Hello, world!' translated_text='Hallo, Welt!'
        ```

Note that the kwarg is `instructions_` with a trailing underscore; this is to avoid conflicts with models that may have a real `instructions` field. If you accidentally pass "instructions" to a model without an "instructions" field, a helpful error will identify your mistake.

Putting this all together, here is a model whose behavior is informed by a docstring on the class itself, an instruction provided to the decorator, and an instruction provided to the instance.

!!! example
    ```python
    @ai_model(instructions="Always set color_2 to 'red'")
    class Test(BaseModel):
        """Always set color_1 to 'orange'"""

        color_1: str
        color_2: str
        color_3: str


    t1 = Test("Hello", instructions_="Always set color_3 to 'blue'")
    assert t1 == Test(color_1="orange", color_2="red", color_3="blue")
    
    ```

### Configuring the LLM
By default, `@ai_model` uses the global LLM settings. To specify a particular LLM, pass it as an argument to the decorator or at instantiation. If you provide it to the decorator, it becomes the default for all uses of that model. If you provide it at instantiation, it is only used for that specific model. 

Note that the kwarg is `model_` with a trailing underscore; this is to avoid conflicts with models that may have a real `model` field. If you accidentally pass a "model" kwarg and there is no "model" field, a helpful error will identify your mistake.

```python
from marvin.engine.language_models import chat_llm


@ai_model(model=chat_llm(model="openai/gpt-3.5-turbo", temperature=0))
class Location(BaseModel):
    city: str
    state: str


print(Location("The Big Apple"))
print(
    Location(
        "The Big Apple",
        model_=chat_llm(model="openai/gpt-3.5-turbo", temperature=1),
    )
)

```