# Marvin Functions


Marvin introduces AI functions that seamlessly blend into your regular Python code. These functions are designed to map diverse combinations of inputs to outputs, without the need to write any source code.

Marvin's functions leverage the power of LLMs to interpret the function's description and inputs, and generate the appropriate output. It's important to note that Marvin does not generate or execute source code, ensuring safety for a wide range of use cases. Instead, it utilizes the LLM as a "runtime" to predict function outputs, enabling it to handle complex scenarios that would be challenging or even impossible to express as code.

Whether you're analyzing sentiment, generating recipes, or performing other intricate tasks, these functions offer a versatile and powerful tool for your natural language processing needs.


<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>fn</code> decorator uses AI to generate outputs for Python functions without source code.
  </p>
</div>

!!! example 
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


## Mapping

Functions can be mapped over sequences of arguments. Mapped functions run concurrently, which means they run practically in parallel (since they are IO-bound). Therefore, the map will complete as soon as the slowest function call finishes.

To see how mapping works, consider this AI Function:


```python
@marvin.fn
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

`marvin.fn` is fully type-safe. It works out of the box with Pydantic models in your function's parameters or return type.


```python
from pydantic import BaseModel
import marvin


class SyntheticCustomer(BaseModel):
    age: int
    location: str
    purchase_history: list[str]


@marvin.fn
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

Marvin exposes an API to prompt a `fn` with natural language. This lets you create a Language API for any function you can write down.


```python
generate_synthetic_customer_data.prompt(
    "I need 10 profiles from rural US cities making between 3 and 7 purchases"
)
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
@marvin.fn
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


@marvin.fn
def create_drip_email(n: int, market_conditions: str) -> list[FinancialReport]:
    """
    Generates `n` synthetic financial reports based on specified
    `market_conditions` (e.g., 'recession', 'bull market', 'stagnant economy').
    """
```


```python
class IoTData(pydantic.BaseModel):
    ...


@marvin.fn
def generate_synthetic_IoT_data(n: int, device_type: str) -> list[IoTData]:
    """
    Generates `n` synthetic data points mimicking those from a specified
    `device_type` in an IoT system.
    """
```
