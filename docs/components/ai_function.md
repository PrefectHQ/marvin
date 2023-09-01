# AI Function

AI Functions are a high-level component, or building block, of Marvin. Like all Marvin components, they are completely standalone: you're free to use them with or without the rest of Marvin.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    <code>@ai_fn</code> is a decorator that lets you use LLMs to generate outputs for Python functions without source code.
  </p>
</div>


```python
from marvin import ai_fn


@ai_fn
def generate_recipe(ingredients: list[str]) -> list[str]:
    """From a list of `ingredients`, generates a
    complete instruction set to cook a recipe.
    """


generate_recipe(["lemon", "chicken", "olives", "coucous"])
```

<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    AI Functions take your function's name, description, signature, source code, type hints, and provided inputs to predict a likely output. By default, no source code is generated and any existing source code is not executed. The only runtime is the LLM.
  </p>
</div>

<div class="admonition tip">
  <p class="admonition-title">When to use</p>
  <p>
    <ol>
    <li> Best for generative tasks: creation and summarization of text or data models.
    <li> Best for writing functions that would otherwise be impossible to write.
    <li> Great for data extraction, though: see AI Models.
    </ol>
  </p>
</div>

## Mapping

AI Functions can be mapped over sequences of arguments. Mapped functions run concurrently, which means they run practically in parallel (since they are IO-bound). Therefore, the map will complete as soon as the slowest function call finishes.

To see how mapping works, consider this AI Function:


```python
@ai_fn
def list_fruit(n: int, color: str = None) -> list[str]:
    """
    Returns a list of `n` fruit that all have the provided `color`
    """
```

Mapping is invoked by using the AI Function's `.map()` method. When mapping, you call the function as you normally would, except that each argument should be a list of items. The function will be called on each set of items (e.g. first with each argument's first item, then with each argument's second item, etc.). For example, this is the same as calling `list_fruit(2)` and `list_fruit(3)` concurrently:


```python
list_fruit.map([2, 3])
```




    [['apple', 'banana'], ['apple', 'banana', 'orange']]



And this is the same as calling `list_fruit(2, color='orange')` and `list_fruit(3, color='red')` concurrently:


```python
list_fruit.map([2, 3], color=["orange", "red"])
```




    [['orange', 'orange'], ['apple', 'strawberry', 'cherry']]



## Features
#### ⚙️ Type Safe

`ai_fn` is fully type-safe. It works out of the box with Pydantic models in your function's parameters or return type.


```python
from pydantic import BaseModel
from marvin import ai_fn


class SyntheticCustomer(BaseModel):
    age: int
    location: str
    purchase_history: list[str]


@ai_fn
def generate_synthetic_customer_data(
    n: int, locations: list[str], average_purchase_history_length: int
) -> list[SyntheticCustomer]:
    """Generates synthetic customer data based on the given parameters.
    Parameters include the number of customers ('n'),
    a list of potential locations, and the average length of a purchase history.
    """


customers = generate_synthetic_customer_data(
    5, ["New York", "San Francisco", "Chicago"], 3
)
```

#### 🗣️ Natural Language API

Marvin exposes an API to prompt an `ai_fn` with natural language. This lets you create a Language API for any function you can write down.


```python
generate_synthetic_customer_data.as_prompt(
    "I need 10 profiles from rural US cities making between 3 and 7 purchases"
)
```

🧪 Code Generation

By default, no code is generated or executed when you call an `ai_fn`. For those who wish to author code, Marvin exposes an experimental API for code generation. Simply call `.code()` on an ai_fn, and Marvin will generate the code for you. By default, Marvin will write python code. You can pass a language keyword to generate code in other languages, i.e. `.code(language = 'rust')`. For best performance give your function a good name, with descriptive docstring, and a signature with type-hints. Provided code will be interpreted as pseudocode. 


```python
from marvin import ai_fn


@ai_fn
def fibonacci(n: int) -> int:
    """
    Returns the nth number in the Fibonacci sequence.
    """


fibonacci.code(language="rust")
```

## Examples

#### Customer Sentiment

<div class="admonition tip">
  <p class="admonition-title">Rapidly prototype natural language pipelines.</p>
  <p>
    Use hallucination as a literal feature. Generate data that would be impossible
    or prohibatively expensive to purchase as you rapidly protype NLP pipelines. 
  </p>
</div>



```python
@ai_fn
def analyze_customer_sentiment(reviews: list[str]) -> dict:
    """
    Returns an analysis of customer sentiment, including common
    complaints, praises, and suggestions, from a list of product
    reviews.
    """


# analyze_customer_sentiment(["I love this product!", "I hate this product!"])
```

#### Generate Synthetic Data

<div class="admonition tip">
  <p class="admonition-title">General real fake data.</p>
  <p>
    Use hallucination as a figurative feature. Use python or pydantic
    to describe the data model you need, and generate realistic data on the fly 
    for sales demos.
  </p>
</div>


```python
class FinancialReport(pydantic.BaseModel):
    ...


@ai_fn
def create_drip_email(n: int, market_conditions: str) -> list[FinancialReport]:
    """
    Generates `n` synthetic financial reports based on specified
    `market_conditions` (e.g., 'recession', 'bull market', 'stagnant economy').
    """
```


```python
class IoTData(pydantic.BaseModel):
    ...


@ai_fn
def generate_synthetic_IoT_data(n: int, device_type: str) -> list[IoTData]:
    """
    Generates `n` synthetic data points mimicking those from a specified
    `device_type` in an IoT system.
    """
```
