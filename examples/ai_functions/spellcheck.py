from marvin import ai_fn


@ai_fn
def spellcheck(text: str) -> str:
    """
    Fixes all spelling and grammar errors  given text and returns the
    corrected text
    """


spellcheck("i can has cheezburger?")  # "I can have a cheeseburger?"
