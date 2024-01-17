"""
Usage example of Marvin with Azure OpenAI

If you'll be using Azure OpenAI exclusively, you can set the following env vars in your environment, `~/.marvin/.env`, or `.env`:
```bash

MARVIN_PROVIDER=azure_openai
MARVIN_AZURE_OPENAI_API_KEY=<your-api-key>
MARVIN_AZURE_OPENAI_ENDPOINT="https://<your-endpoint>.openai.azure.com/"
MARVIN_AZURE_OPENAI_API_VERSION=2023-12-01-preview # or latest

Note that you MUST set the LLM model name to be your Azure OpenAI deployment name, e.g.
MARVIN_CHAT_COMPLETION_MODEL=<your Azure OpenAI deployment name>
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
    provider="azure_openai",
    azure_openai_api_key="...",
    azure_openai_api_version="...",
    azure_openai_endpoint="...",
    chat_completion_model="<your Azure OpenAI deployment name>",
):
    fruits = list_fruits()
    location = marvin.model(Location)("windy city")
    casted_location = marvin.cast("windy city", Location)
    extracted_locations = marvin.extract("I live in Chicago", Location)
    sentiment = marvin.classify("I love this movie", Sentiment)

print(fruits)
print(location, casted_location, extracted_locations)
print(sentiment)
