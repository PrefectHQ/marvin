from marvin import ai_fn


@ai_fn
def joke_of_the_day() -> list[str]:
    """Generates a random punny joke of the day"""


print(joke_of_the_day())

# Why did the tomato turn red? because it saw the salad dressing!
