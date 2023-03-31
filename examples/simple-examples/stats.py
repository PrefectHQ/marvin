from marvin import ai_fn


@ai_fn()
def stats(stats: list[float]) -> list[str]:
    """return the mean, median, and mode of a list of numbers"""


print(stats([2, 3, 43, 2, 5, 9, 88, 7]))

# ["mean: 20.375", "median: 5.0", "mode: 2"]
