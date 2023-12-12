<p align="center">
  <img src="docs/img/heroes/it_hates_me_hero.png" style="width: 95%; height: auto;"/>
</p>

# Marvin
### An engineering framework
... made with 💙 by the team at [Prefect](https://www.prefect.io/)

[![PyPI version](https://badge.fury.io/py/marvin.svg)](https://badge.fury.io/py/marvin)
[![Twitter Follow](https://img.shields.io/twitter/follow/AskMarvinAI?style=social)](https://twitter.com/AskMarvinAI)

## Documentation
Marvin's docs are available at [askmarvin.ai](https://www.askmarvin.ai), including concepts, tutorials, and an API reference.

```bash
pip install marvin
```
Getting started? Head over to our [setup guide](https://www.askmarvin.ai/welcome/installation/).

## Community
To ask questions, share ideas, or just chat with like-minded developers, join us on [Discord](https://discord.gg/Kgw4HpcuYG) or [Twitter](https://twitter.com/AskMarvinAI)!


## Offerings

Marvin's high-level abstractions are familiar Python interfaces that make it easy to leverage AI in your application. These interfaces aim to be simple and self-documenting, adding a touch of AI magic to everyday objects.

🪄 [**AI Functions**](https://www.askmarvin.ai/components/ai_function/) for complex business logic and transformations

🧩 [**AI Models**](https://www.askmarvin.ai/components/ai_model/) for structuring text into type-safe schemas

🤖 (*beta*) [**Assistants**](/src/marvin/beta/assistants/README.md) for building stateful natural language interfaces
___

### 🪄 AI Functions

AI Functions look like regular functions, but have no source code. Instead, an AI uses their description and inputs to generate their outputs, making them ideal for NLP applications like sentiment analysis. 

You can learn more about AI Functions [here](https://www.askmarvin.ai/components/ai_function/).


```python
from marvin import ai_fn


@ai_fn
def sentiment(text: str) -> float:
    """
    Given `text`, returns a number between 1 (positive) and -1 (negative)
    indicating its sentiment score.
    """


sentiment("I love working with Marvin!") # 0.8
sentiment("These examples could use some work...") # -0.2
```

```python
from typing_extensions import TypedDict

class DetailedSentiment(TypedDict):
    """
    A detailed sentiment analysis result.

    - `sentiment_score` is a number between 1 (positive) and -1 (negative)
    - `summary_in_a_word` is a one-word summary of the general sentiment, 
        use any apt word that captures the nuance of the sentiment
    """
    sentiment_score: float
    summary_in_a_word: str

@ai_fn
def detailed_sentiment(text: str) -> DetailedSentiment:
    """What do you think the sentiment of `text` is?
    
    Use your theory of mind to put yourself in the shoes of its author.
    """

detailed_sentiment("I'ma Mario, I'ma gonna wiiiiin!") # {'sentiment_score': 0.8, 'summary_in_a_word': 'energetic'}
```

### 🧩 AI Models

Marvin's most basic component is the AI Model, a drop-in replacement for Pydantic's `BaseModel`. AI Models can be instantiated from any string, making them ideal for structuring data, entity extraction, and synthetic data generation. 

You can learn more about AI models [here](https://www.askmarvin.ai/components/ai_model/).

```python
from marvin import ai_model
from pydantic import BaseModel, Field


@ai_model
class Location(BaseModel):
    city: str
    state: str = Field(..., description="The two-letter state abbreviation")


Location("The Big Apple")
# Location(city='New York', state='NY')
```

## Assistants (Beta)
Based on OpenAI's Assistant API, Marvin's Assistants are the easiest way to build a stateful natural language interface equipped with familiar tools (i.e. python functions).
```python
from marvin.beta.assistants import Assistant, Thread

def multiply(x: float, y: float) -> float:
    return x * y

def divide(x: float, y: float) -> float:
    return x / y


with Assistant(tools=[multiply, divide]) as assistant:
    thread = Thread()
    while True:
        message = input("You: ")
        if message.lower() in ["exit", ":q", "bye"]:
            break
        thread.add(message)
        thread.run(assistant)
        print("\n\n".join(m.content[0].text.value for m in thread.get_messages()))
        # what is the speed of light (m/s) times the number of days in a year?

        # what is that number divided by 42?
```

Read more about [our SDK](/src/marvin/beta/assistants/README.md) and/or the [OpenAI docs](https://platform.openai.com/docs/assistants/overview).