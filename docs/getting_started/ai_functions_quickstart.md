# AI Functions

![](../img/heroes/ai_fn_fruits_hero.png)

AI functions are powerful, flexible, and super simple. They rely on the doc string, parameter(s), and the type annotation. Whereas a doc string in a typical function is very much _not_ the code, the AI function's doc string essentially _is the code_ that enables the bot to take simple, local inputs and use AI to generate their outputs. Like normal functions, AI functions take arguments and return structured outputs like `lists`, `dicts` or even Pydantic models. Unlike normal functions, they don't need any source code! 

Consider the following example, which contains a function that generates a list of fruits. The function is defined with a descriptive name, annotated input and return types, and a docstring -- but doesn't appear to actually do anything. Nonetheless, because of the `@ai_fn` decorator, it can be called like a normal function and returns a list of fruits.

```python hl_lines="4"
from marvin import ai_fn


@ai_fn
def list_fruits(n: int) -> list[str]:
    """Generate a list of n fruits"""


list_fruits(n=3) # ["apple", "banana", "orange"]
```

AI functions are especially useful for activies that would be difficult, time-consuming, or impossible to code. They are particularly powerful for parsing and processing strings, but can be used with almost any data structure. Here are a few more examples:

```python
@ai_fn
def extract_animals(text: str) -> list[str]:
    """Returns a list of all animals mentioned in the text"""
```
```python
@ai_fn
def classify_sentiment(tweets: list[str]) -> list[bool]:
    """
    Given a list of tweets, classifies each one as 
    positive (true) or negative (false) and returns 
    a corresponding list
    """
```
```python
@ai_fn
def suggest_title(article: str, style: str=None) -> str:
    """
    Suggest a title for the provided article, optionally in 
    the style of a publication (such as the AP, NYTimes, etc.)
    """
```
```python
@ai_fn
def extract_keywords(text:str, criteria:str=None) -> list[str]:
    """
    Extract important keywords from text, optionally only including 
    those that meet the provided criteria (for example, "colors", 
    "proper nouns", or "European capitals")
    """
```

For more information about AI functions, including examples and how to include executable code in your function, see the [AI function docs](ai_functions.md).
