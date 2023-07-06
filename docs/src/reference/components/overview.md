
# AI Components

Marvin introduces a number of components that can become the building blocks of AI-powered software.

## AI Models
[AI Models](/src/reference/components/ai_model/) are a drop-in replacement for Pydantic's `BaseModel` that can be parsed from natural language. AI Models can be used for structuring data, entity extraction, and synthetic data generation. 
  
```python
from marvin import ai_model


@ai_model
class Location(pydantic.BaseModel):
    city: str
    state: str


Location("The Big Apple") 
# Equivalent to:
# Location(city='New York City', state='New York')
```

## AI Functions
[AI Functions](/src/reference/components/ai_model/) are Python functions that do not require source code. They can use an LLM as a runtime to generate outputs. 

```python
from marvin import ai_fn


@ai_fn
def classify_sentiment(text: str) -> float:
    """
    Classifies the sentiment of `text` as a precise value between -1 (very 
    negative) and 1 (very positive).
    """


classify_sentiment("I can't wait to visit the zoo!") 
# Returns:
# 0.8
```
