from marvin import ai_fn


@ai_fn()
def mad_libs(n: int) -> list[str]:
    """Returns a 100-word to 200-word mad lib with {n} blanks.
    All the blanks should be adjectives.
    """


print(mad_libs(n=3))

# ['Aardvarks can be ____, ____ and ____ animals.']
# Note: works sometimes with gpt-3.5-turbo, and not 100 words
