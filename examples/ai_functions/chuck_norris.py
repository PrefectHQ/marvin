from marvin import ai_fn
import os

@ai_fn
def chuck_norris_joke_of_the_day(howmany: int = 3, modifier : str = "") -> list[str]:
    """Generates a {howmany} random Chuck Norris jokes of the day, {modifier}"""

@ai_fn
def chuck_norris_joke_of_the_day_clean(howmany: int = 3) -> list[str]:
   chuck_norris_joke_of_the_day(howmany, "but all G-Rated")

print(chuck_norris_joke_of_the_day(3))