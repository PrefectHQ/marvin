# AI Functions Examples

## Generate a list of fruits
```python
from marvin import ai_fn

@ai_fn
def list_fruits(n: int) -> list[str]:
    """Generate a list of n fruits"""


list_fruits(3) # ["apple", "banana", "orange"]
```

## Generate fake data according to a schema
```python
from marvin import ai_fn

@ai_fn
def fake_people(n: int) -> list[dict]:
    """
    Generates n examples of fake data representing people, 
    each with a name and an age.
    """


fake_people(3)
# [{'name': 'John Doe', 'age': 29},
#  {'name': 'Jane Smith', 'age': 34},
#  {'name': 'Alice Johnson', 'age': 42}]
```

## Correct spelling and grammar

```python
from marvin import ai_fn

@ai_fn
def fix_sentence(sentence: str) -> str:
    """
    Fix all grammatical and spelling errors in a sentence
    """

fix_sentence("he go to mcdonald and buy burg") # "He goes to McDonald's and buys a burger."
```

## Cleaning data
Cleaning data is such an important use case that Marvin has an entire module dedicated to it, including AI functions for categorization, standardization, entity extraction, and context-aware fills for missing values. See [the data cleaning documentation](/guide/ai_functions/data) for more information.
## Unit testing LLMs
One of the difficulties of building an AI library is unit testing it! While it's possible to make LLM outputs deterministic by setting the temperature to zero, a small change to a prompt could result in very different outputs. Therefore, we want a way to assert that an LLM's output is "approximately equal" to an expected value.

This example is actually used by Marvin itself! See `marvin.utilities.tests.assert_llm()`.

```python
@ai_fn()
def assert_llm(output: Any, expectation: Any) -> bool:
    """
    Given the `output` of an LLM and an expectation, determines whether the
    output satisfies the expectation.

    For example:
        `assert_llm(5, "output == 5")` will return `True` 
        `assert_llm(5, 4)` will return `False` 
        `assert_llm(["red", "orange"], "a list of colors")` will return `True` 
        `assert_llm(["red", "house"], "a list of colors")` will return `False`
    """

assert_llm('Hello, how are you?', expectation='Hi there') # True
```
## Summarize text

This function takes any text and summarizes it. See the next example for a
function that can also access Wikipedia automatically.

```python
from marvin import ai_fn

@ai_fn
def summarize(text: str) -> str:
    """
    Summarize the provided text
    """

import wikipedia
page = wikipedia.page('large language model')
summarize(text=page.content)
# Large language models (LLMs) are neural networks with billions of parameters
# trained on massive amounts of unlabelled text. They excel at various tasks and
# can capture much of human language's syntax and semantics. LLMs use the
# transformer architecture and are trained using unsupervised learning. Their
# applications include fine-tuning and prompting for specific natural language
# processing tasks.
```

## Summarize text after loading a Wikipedia page

This example demonstrates how `ai_fn` can call a function to get additional information that can be used in producing a result. Here, the function downloads content from Wikipedia given a title.

```python
from marvin import ai_fn

@ai_fn
def summarize_from_wikipedia(title: str) -> str:
    """
    Loads the wikipedia page corresponding to the provided 
    title and returns a summary of the content.
    """
    import wikipedia
    page = wikipedia.page(title)

    # the content to summarize
    yield page.content


summarize_from_wikipedia(title='large language model')
# A large language model (LLM) is a language model consisting of a neural
# network with many parameters (typically billions of weights or more), trained
# on large quantities of unlabelled text using self-supervised learning. LLMs
# emerged around 2018 and perform well at a wide variety of tasks. This has
# shifted the focus of natural language processing research away from the
# previous paradigm of training specialized supervised models for specific
# tasks.
```

## Suggest a title after loading a URL

This example demonstrates how `ai_fn` can call a function to get additional information that can be used in producing a result. Here, the function loads an article and then suggests a title for it.

```python
from marvin import ai_fn

@ai_fn
def suggest_title(url: str) -> str:
    """
    Suggests a title for the article found at the provided URL
    """

    import httpx

    # load the url
    response = httpx.get(url)

    # return the url contents 
    yield marvin.utilities.strings.html_to_content(response.content)


suggest_title(url="https://techcrunch.com/2023/03/14/openai-releases-gpt-4-ai-that-it-claims-is-state-of-the-art/")
# OpenAI Releases GPT-4: State-of-the-Art AI Model with Improved Image and Text Understanding
```

## Generate rhymes

```python
from marvin import ai_fn

@ai_fn
def rhyme(word: str) -> str:
    """
    Generate a word that rhymes with the supplied `word`
    """

rhyme("blue") # glue
```

## Find words meeting specific criteria

```python
from marvin import ai_fn

@ai_fn
def find_words(text: str, criteria: str) -> list[str]:
    """
    Given text and some criteria, returns a list of 
    every word meeting that criteria.
    """

text = "The quick brown fox jumps over the lazy dog."
find_words(text, criteria="adjectives") # ["quick", "brown", "lazy"]
find_words(text, criteria="colors") # ["brown"]
find_words(text, criteria="animals that aren't dogs") # ["fox"]
```



## Suggest emojis

```python
from marvin import ai_fn

@ai_fn
def get_emoji(text: str) -> str:
    """
    Returns an emoji that describes the provided text.
    """

get_emoji("incredible snack") # '🍿'
```


## Generate RRULEs
RRULE strings are standardized representations of calendar events. This AI
function can convert natural language into an RRULE.

This is also available as a builtin function: `marvin.ai_functions.strings.rrule`

```python

from marvin import ai_fn

@ai_fn
def rrule(text: str) -> str:
    """
    Generate valid RRULE strings from a natural language description of an event
    """
    yield pendulum.now.isoformat()

rrule('every hour from 9-6 on thursdays')
# "RRULE:FREQ=WEEKLY;BYDAY=TH;BYHOUR=9,10,11,12,13,14,15,16;BYMINUTE=0;BYSECOND=0"
```

## Get a datetime from a natural language description

```python
from datetime import datetime

from marvin import ai_fn

@ai_fn
def make_datetime(description: str, tz: str = "BST") -> datetime:
    """ generates a datetime from a description """

# !date +"%Y-%m-%d %T %Z"
# 2023-06-23 22:30:25 BST

dt = make_datetime("5 mins from now")
# datetime.datetime(2023, 6, 23, 22, 35, tzinfo=datetime.timezone(datetime.timedelta(seconds=3600)))

dt.isoformat()
# '2023-06-23T22:35:00+01:00'
```