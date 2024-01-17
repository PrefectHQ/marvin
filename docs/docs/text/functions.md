# AI Functions


Marvin introduces "AI functions" that seamlessly blend into your regular Python code. These functions are designed to map diverse combinations of inputs to outputs, without the need to write any source code.

Marvin's functions leverage the power of LLMs to interpret the function's description and inputs, and generate the appropriate output. It's important to note that Marvin does not generate or execute source code, ensuring safety for a wide range of use cases. Instead, it utilizes the LLM as a "runtime" to predict function outputs, enabling it to handle complex scenarios that would be challenging or even impossible to express as code.

Whether you're analyzing sentiment, generating recipes, or performing other intricate tasks, these functions offer a versatile and powerful tool for your natural language processing needs.


<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>fn</code> decorator uses AI to generate outputs for Python functions without any source code.
  </p>
</div>

!!! example 
    Quickly create a function that can return a sentiment score for any text:

    ```python
    
    @marvin.fn
    def sentiment(text: str) -> float:
        """
        Returns a sentiment score for `text` 
        between -1 (negative) and 1 (positive).
        """
    ```
    
    !!! success "Result"
    
        ```python
        sentiment("I love working with Marvin!") # 0.8
        sentiment("These examples could use some work...") # -0.2
        ```


<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin uses your function's name, description, signature, source code, type hints, and provided inputs to predict a likely output. No source code is generated and any existing source code is not executed. The only runtime is the large language model.
  </p>
</div>

## Types

Marvin functions are *real* functions in that they can be called and return values, just like any other function. The "magic" happens inside the function, when it calls out to an LLM to generate its output. Therefore, you can use Marvin functions anywhere you would use a normal function, including in other Marvin functions.

This means that you must also design your functions carefully, just like you would any other function. For example, if you do not provide a required argument or provide an unexpected argument, Python will error before the LLM is called. Marvin will also respect any default arguments that your provide.

The result of your function is also a Python type, according to your function's signature. There are exceptions: an untyped function or a function annotated with `-> None` will return a string instead.


## Defining a function

Marvin uses all available information to infer the behavior of your function. The more information you provide, the higher quality the output will be. There are a few key ways to provide instructions, most importantly the name of the function, its arguments and their types, its docstring, and the return value. For advanced use cases, you can also write source code that will *not* be shown to to the LLM, but any return value will be provided as additional context.

### Docstring
The function's docstring is perhaps the most important source of information for the LLM. It should describe the function's behavior in plain English, and can include examples, notes, and other information that will help the LLM understand the function's purpose.

The docstring can refer to the function's arguments by name or interpolate the argument's value at runtime. This function references the `n` argument in the docstring explicitly, similar to how a normal Python function would be documented:

```python
@marvin.fn
def list_fruit(n: int) -> list[str]
    """
    Returns a list of `n` fruit.
    """
```

When the above function is called with `n=3`, the LLM will see the string ``"... of `n` fruit"``, exactly as written, and also see `n=3` as context. It will use inference to understand the instruction.

#### Templating

If the docstring is written in jinja notation, Marvin will template variable names into it before sending the prompt to the LLM. Consider this slightly modified version of the above function (note the `{{n}}` instead of `` `n` ``):
```python
@marvin.fn
def list_fruit(n: int) -> list[str]
    """
    Returns a list of {{n}} fruit.
    """
```

When this function is called with `n=3`, the LLM will see the string ``"... of 3 fruit"`` (and it will also see the argument value). You can use this technique to adjust how the LLM sees the interaction of runtime arguments and the docstring instructions.

### Parameters

The function's parameters, in conjunction with the docstring, provide the LLM with runtime context. The LLM will see the parameter names, types, defaults, and runtime values, and use this information to generate the output. Parameters are important for collecting information, but because the information is ultimately going to an LLM, they can be named anything and take any value that is conducive to generating the right output. 
or example, if you have a function that returns a list of recipes, you might define it like this:

```python
@marvin.fn
def recipe(
    ingredients: list[str], 
    max_cook_time: int = 15, 
    cuisine: str = "North Italy", 
    experience_level="beginner"
) -> str:
    """
    Returns a complete recipe that uses all the `ingredients` and 
    takes less than `max_cook_time`  minutes to prepare. Takes 
    `cuisine` style and the chef's `experience_level` into account 
    as well. Recipes have a name, list of ingredients, and steps to follow.
    """
```

Now we can call this function in ways that would be impossible to code in Python:

=== "Novice chef"

    ```python
    recipe(
        ["chicken", "potatoes"], 
        experience_level='can barely boil water'
    )
    ```


    !!! success "Result"
        Recipe for Simple North Italian Chicken and Potatoes
        
        Ingredients:

        - Chicken
        - Potatoes
        
        Instructions:

        1. Wash the potatoes and cut them into quarters.
        2. Place potatoes in a microwave-safe dish, cover with water, and microwave for 10 minutes until soft.
        ...
    

=== "Expert chef"

    ```python
    recipe(
        ["chicken", "potatoes"], 
        max_cook_time=60, 
        experience_level='born wearing a toque'
    )
    ```


    !!! success "Result"
        
        Recipe Name: Herbed Chicken with Roasted Potatoes
        
        Ingredients:
        
        - Chicken
        - Potatoes
        - Olive oil
        - Rosemary
        - Salt
        - Black pepper
        - Garlic (optional)
        
        Steps:
        
        1. Preheat your oven to 200 degrees Celsius (392 degrees Fahrenheit).
        2. Wash and cut the potatoes into chunks, then toss them with olive oil, salt, rosemary, and black pepper. Place them on a baking tray.
        ...
        
### Return annotation

Marvin will cast the output of your function to the type specified in the return annotation. If you do not provide a return annotation, Marvin will assume that the function returns a string. 

The return annotation can be any valid Python type, including Pydantic models, `Literals`, and `TypedDicts`. The only exception is `None`/`empty`, which will return a string instead. 

To indicate that you want to return multiple objects, use `list[...]` as the return annotation.

```python
from pydantic import BaseModel

class Attraction(BaseModel):
    name: str
    category: str
    city: str
    state: str

@marvin.fn
def sightseeing(destination:str, goal: str) -> list[Attraction]:
    '''
    Return a list of 3 attractions in `destination` that 
    are related to the tourist's `goal`.
    '''

attractions = sightseeing('NYC', 'museums')
```

!!! success "Result"
    ```python
    attractions == [
        Attraction(
            name="Metropolitan Museum of Art",
            category="Art Museum",
            city="New York",
            state="NY",
        ),
        Attraction(
            name="Museum of Modern Art", 
            category="Art Museum", 
            city="New York", 
            state="NY"
        ),
        Attraction(
            name="American Museum of Natural History",
            category="Natural History Museum",
            city="New York",
            state="NY",
        ),
    ]
    ```
    

### Name

The function's name is sent to the LLM, so it's important to choose a name that accurately describes the function's behavior. For example, if you're creating a function that returns the sentiment of a text, you might name it `sentiment`. If you're creating a function that returns a list of recipes, you might name it `recipes`.

### Returning values from functions

For advanced use cases, you can return values from your function that will be provided to the LLM as additional context. This is useful for providing information that may require some retreival step, programmatic enhancement, or conditional logic. While you could do this by wrapping your Marvin function in another function and providing the processed inputs directly, this approach is more flexible and allows you to use the same function in different contexts.

Note that the LLM will not see the source code of your function even if you add any. It will only see the return value. This is to avoid confusing it about the function's purpose.

```python
import requests

@marvin.fn
def summarize_url(url: str) -> str:
    """
    Returns a summary of the contents of `url`.
    """
    # return the text found at the URL
    return requests.get(url).content

summarize_url('https://www.askmarvin.ai')

# Marvin is a lightweight AI engineering framework for building natural language
# interfaces that are reliable, scalable, and easy to trust. It offers a Getting
# Started guide, Cookbook, Docs, API Reference, Community support, and several
# other resources to help with the development of AI-based applications.
```

## Running a function
Running a function is quite simple: just call it like you would any other function! The LLM will generate the output based on the function's definition and the provided inputs. Remember that no source code is generated or executed, so every call to the function will be handled by the LLM. You can use caching or other techniques to improve performance if necessary.