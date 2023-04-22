# AI Functions for entities

AI functions are powerful tools for extracting structured data from unstructured text.

## Extract keywords

```python
from marvin.ai_functions.entities import extract_keywords


text = (
    'The United States passed a law that requires all cars to have a "black'
    ' box" that records data about the car and its driver. The law is sponsored'
    " by John Smith. It goes into effect in 2025."
)

extract_keywords(text)
# ["United States", "law", "cars", "black box", "records", "data", "driver", "John Smith", "2025"]
```

## Extract named entitites

This function extracts named entities, tagging them with spaCy-compatible types:

```python
from marvin.ai_functions.entities import extract_named_entities


text = (
    'The United States passed a law that requires all cars to have a "black'
    ' box" that records data about the car and its driver. The law is sponsored'
    " by John Smith. It goes into effect in 2025."
)

extract_named_entities(text)
# [
#     NamedEntity(entity="United States", type="GPE"),
#     NamedEntity(entity="John Smith", type="PERSON"),
#     NamedEntity(entity="2025", type="DATE"),
# ]
```


## Extract any type of entity

A more flexible extraction function can retrieve multiple entity types in a single pass over the text. Here we pull countries and monetary values out of a sentence:

```python
from pydantic import BaseModel
class Country(BaseModel):
    name: str

class Money(BaseModel):
    amount: float
    currency: str

text = "The United States EV tax credit is $7,500 for cars worth up to $50k."
extract_types(text, types=[Country, Money])

# [
#     Country(name="United States"),
#     Money(amount=7500, currency="USD"),
#     Money(amount=50000, currency="USD"),
# ]
```
