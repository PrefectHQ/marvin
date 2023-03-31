import marvin
from marvin import ai_fn
from marvin.plugins.duckduckgo import DuckDuckGo
from pydantic import BaseModel


class Weather(BaseModel):
    temperature: float
    humidity: float
    wind_speed: float
    wind_direction: float
    pressure: float


@ai_fn(plugins=[DuckDuckGo()])
def find_weather_in_place(place: str) -> Weather:
    """Find the weather in a place using DuckDuckGo."""


marvin.settings.log_level = "DEBUG"
print(find_weather_in_place("London"))
