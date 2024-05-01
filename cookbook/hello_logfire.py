"""
Example of using logfire to instrument OpenAI API calls

see https://x.com/Nathan_Nowack/status/1785413529232708087
"""

import logfire
import openai
from marvin import fn
from marvin.client import AsyncMarvinClient
from pydantic import BaseModel, Field

client = openai.AsyncClient()

logfire.instrument_openai(client)


class Ingredients(BaseModel):
    name: str
    approximate_price: float = Field(..., gt=0, description="Price in USD")
    quantity: int


class Recipe(BaseModel):
    ingredients: list[Ingredients]
    steps: list[str]


@fn(client=AsyncMarvinClient(client=client))
def make_recipe(vibe: str) -> Recipe:
    """Generate a recipe based on a vibe"""


if __name__ == "__main__":
    recipe = make_recipe("italian, for 4 people")
    assert isinstance(recipe, Recipe)
