"""Usage example of Marvin with Azure OpenAI

If you'll be using Azure OpenAI exclusively, you can set the following environment variables in `~/.marvin/.env`:
```bash
MARVIN_USE_AZURE_OPENAI=true
MARVIN_AZURE_OPENAI_API_KEY=...
MARVIN_AZURE_OPENAI_API_VERSION=...
MARVIN_AZURE_OPENAI_ENDPOINT=...
MARVIN_AZURE_OPENAI_DEPLOYMENT_NAME=...
```
"""
from enum import Enum

import marvin
from marvin.settings import temporary_settings
from pydantic import BaseModel


class Sentiment(Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class Location(BaseModel):
    city: str
    state: str
    country: str


@marvin.fn
def list_fruits(n: int = 3) -> list[str]:
    """generate a list of fruits"""


with temporary_settings(
    use_azure_openai=True
):  # or set MARVIN_USE_AZURE_OPENAI=true in `~/.marvin/.env`
    fruits = list_fruits()
    location = marvin.model(Location)("windy city")
    casted_location = marvin.cast("windy city", Location)
    extracted_locations = marvin.extract("I live in Chicago", Location)
    sentiment = marvin.classify("I love this movie", Sentiment)

print(fruits)
print(location, casted_location, extracted_locations)
print(sentiment)
