# Quickstart

## Basic Installation

You can install Marvin with `pip` (note that Marvin requires Python 3.9+):

```shell
pip install marvin
``` 

You can upgrade to the latest released version at any time:

```shell
pip install marvin -U
```

!!! warning "Breaking changes in 2.0"
    Please note that Marvin 2.0 introduces a number of breaking changes and is not compatible with Marvin 1.X.

The fastest way to get started is by using one of Marvin's high-level components. These components are designed to integrate AI into abstractions you already know well, creating the best possible opt-in developer experience.

### Configure LLM Provider

Marvin is a high-level interface for working with LLMs. At this time, Marvin supports OpenAI's GPT-3.5 and GPT-4 models, and the Azure OpenAI Service. The default model is OpenAI's `gpt-3.5-turbo`. To use the default model, provide an API key:

```python
from marvin.settings import settings

# to use an OpenAI model (if not specified, defaults to gpt-4)
marvin.settings.openai.api_key = YOUR_API_KEY
```


## High Level Components

### AI Models

Marvin's most basic component is the AI Model, a drop-in replacement for Pydantic's `BaseModel`. AI Models can be instantiated from any string, making them ideal for structuring data, entity extraction, and synthetic data generation:

```python
from marvin import ai_model
from pydantic import BaseModel, Field


@ai_model
class Location(BaseModel):
    city: str
    state: str = Field(..., description="The two-letter state abbreviation")


Location("The Big Apple")
```

    Location(city='New York', state='NY')

### AI Classifiers

AI Classifiers let you build multi-label classifiers with no code and no training data. Given user input, each classifier uses a [clever logit bias trick](https://twitter.com/AAAzzam/status/1669753721574633473) to force an LLM to deductively choose the best option. It's bulletproof, cost-effective, and lets you build classifiers as quickly as you can write your classes.

```python
from marvin.components import ai_classifier
from enum import Enum

class AppRoute(Enum):
    NOTIFICATIONS = "/notifications"
    SETTINGS = "/settings"
    HELP = "/help"
    CHAT = "/chat"
    DOCS = "/docs"
    PROJECTS = "/projects"

@ai_classifier
def classify_user_intent(text: str) -> AppRoute:
    '''
        Chooses the most likely route
    '''

classify_user_intent("change my username") #<AppRoute.SETTINGS: '/settings'>

```

    <AppRoute.USER_PROFILE: '/user-profile'>

### AI Functions

AI Functions look like regular functions, but have no source code. Instead, an AI uses their description and inputs to generate their outputs, making them ideal for NLP applications like sentiment analysis.

```python
from marvin import ai_fn


@ai_fn
def sentiment(text: str) -> float:
    """
    Given `text`, returns a number between 1 (positive) and -1 (negative)
    indicating its sentiment score.
    """


sentiment("I love working with Marvin!") #.8
sentiment("These examples could use some work...") #-.2
```

Because AI functions are just like regular functions, you can quickly modify them for your needs. Here, we modify the above example to work with multiple strings at once:

```python
from marvin import ai_fn


@ai_fn
def sentiment_list(texts: list[str]) -> list[float]:
    """
    Given a list of `texts`, returns a list of numbers between 1 (positive) and
    -1 (negative) indicating their respective sentiment scores.
    """


sentiment_list(
    [
        "That was surprisingly easy!",
        "Oh no, not again.",
    ]
) # 0.7, -0.5]
```
## Lower Level Components

### Prompt Functions

Marvin's prompt_fn only creates a prompt to send to a large language model. It does not call any external service, it's simply responsible for translating your query into something that a large language model will understand. It follows OpenAI's function calling syntax.

```python
import pydantic
from marvin import prompt_fn

class City(pydantic.BaseModel):
    '''
        A model to represent a city.
    '''

    text: str = pydantic.Field(
        description = 'The city name as it appears'
    )

    inferred_city: str = pydantic.Field(
            description = 'The inferred and normalized city name.'
        )

@prompt_fn
def get_cities(text: str) -> list[City]:
    '''
        Expertly deduce and infer all cities from the follwing text: {{ text }}
    '''

```

Here's the output when we plug in a few cities.

```python
get_cities("Chicago, The Windy City, New York City, the Big Apple.")
```
??? "Click to see output"

    ```json
    {
    "messages": [
        {
        "role": "system",
        "content": "Expertly deduce and infer all cities from the follwing text: Chicago, The Windy City, New York City, the Big Apple, SF, San Fran, San Francisco."
        }
    ],
    "functions": [
        {
        "parameters": {
            "$defs": {
            "City": {
                "description": "A model to represent a city.",
                "properties": {
                "text": {
                    "description": "The city name as it appears",
                    "title": "Text",
                    "type": "string"
                },
                "inferred_city": {
                    "description": "The inferred and normalized city name.",
                    "title": "Inferred City",
                    "type": "string"
                }
                },
                "required": [
                "text",
                "inferred_city"
                ],
                "title": "City",
                "type": "object"
            }
            },
            "properties": {
            "output": {
                "items": {
                "$ref": "#/$defs/City"
                },
                "title": "Output",
                "type": "array"
            }
            },
            "required": [
            "output"
            ],
            "type": "object"
        },
        "name": "Output",
        "description": ""
        }
    ],
    "function_call": {
        "name": "Output"
    }
    }
    ```