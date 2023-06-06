from marvin import ai_fn


@ai_fn
def chuck_norris_joke_of_the_day(howmany: int = 3, modifier: str = "") -> list[str]:
    if modifier is not None:
        """Generates {howmany} random Chuck Norris jokes of the day, {modifier}"""
    """Generates {howmany} random Chuck Norris jokes of the day"""


@ai_fn
def chuck_norris_joke_of_the_day_clean(howmany: int = 3) -> list[str]:
    chuck_norris_joke_of_the_day(howmany, "but all G-Rated")


@ai_fn
def chuck_norris_joke_of_the_day_geek(howmany: int = 3) -> list[str]:
    chuck_norris_joke_of_the_day(howmany, "but all Math related")


print(chuck_norris_joke_of_the_day())
# ['Chuck Norris once ate an entire bottle of sleeping pills. They made him
# blink.', "Chuck Norris doesn't need to flush the toilet. He simply scares the
# shit out of it.", "Chuck Norris doesn't use web standards as the web will
# conform to him."]

print(chuck_norris_joke_of_the_day_clean())
# ['Chuck Norris can divide by zero.', 'Chuck Norris counted to infinity...
# twice.', "Chuck Norris doesn't wear a watch. He decides what time it is."]

print(chuck_norris_joke_of_the_day_geek())
# ["Mathematics is not about numbers, it's about figuring out how to eat cake
# and lose weight at the same time - Chuck Norris", "Chuck Norris once solved a
# Rubik's cube in one move...but forgot what the original colors were", "The
# square root of Chuck Norris is...well, you don't want to know - but it's
# definitely not a real number!"]
