from pydantic import BaseModel

import marvin
from marvin.experimental import ai_fn, ai_model

marvin.settings.llm_model = "gpt-3.5-turbo-0613"
marvin.settings.log_level = "DEBUG"


@ai_model
class Location(BaseModel):
    city: str
    state: str
    lat: float
    long: float


@ai_fn
def list_fruit(n: int) -> list[str]:
    """Generate a list of n fruit"""


@ai_fn
def generate_people(n: int) -> list[dict]:
    """Generate a list of n people who have ages,  names, and locations"""


class Person(BaseModel):
    name: str
    age: int
    location: Location


@ai_fn
def generate_people_pydantic(n: int) -> list[Person]:
    """Generate a list of n people"""
