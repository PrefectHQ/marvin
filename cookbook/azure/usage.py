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
    sentiment = marvin.classify("I love this movie", Sentiment)

print(fruits)
print(location)
print(sentiment)
