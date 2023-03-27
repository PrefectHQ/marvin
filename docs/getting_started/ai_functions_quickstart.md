# AI Functions

**AI functions** are functions that use AI to generate their outputs - without ever writing source code. Like normal functions, they can take arguments and return structured outputs like `lists`, `dicts` or even Pydantic models.

```python hl_lines="4"
from marvin import ai_fn


@ai_fn
def list_fruit(n: int) -> list[str]:
    """Generate a list of n fruit"""


list_fruit(3) # ["apple", "banana", "orange"]
```

Applying the `@ai_fn` decorator is all it takes to send a function definition like `list_fruit` and send it to an AI for processing. For best results, your function should include a descriptive name, annotated inputs, an annotated return type, and a docstring. 

AI functions are especially useful for working with strings in ways that are difficult or time-consuming to code:

```python
@ai_fn
def extract_animals(text: str) -> list[str]:
    """Returns a list of all animals mentioned in the text"""

@ai_fn
def classify_sentiment(tweets: list[str]) -> list[bool]:
    """
    Given a list of tweets, classifies each one as 
    positive (true) or negative (false) and returns 
    a corresponding list
    """
```

For more information about AI functions, including examples and how to include executable code in your function, see the [AI function docs](ai_functions.md).