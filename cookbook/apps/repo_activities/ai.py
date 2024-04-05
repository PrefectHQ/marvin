import marvin


@marvin.fn(model_kwargs={"model": "gpt-3.5-turbo"})
async def describe_event_as_key(event_digest: str) -> str:
    """given an event digest, produce descriptive key in the following format:

    `about_{KEYWORD_1}_{KEYWORD_2}`

    where `KEYWORD_1` `KEYWORD_2` are the most semantically representative words
    of the event digest. the keywords need not be present in the event digest, only
    semantically representative.

    `about_` should be present in each key and the key should always be a total
    of 3 lowercase words separated by 2 underscores. e.g. `about_broken_imports`
    """


@marvin.fn(model_kwargs={"model": "gpt-3.5-turbo", "temperature": 1.2})
def say_you_are_healthy(in_the_style_of: str = "Top Boy (UK tv show)") -> str:
    """give an extremely short message that you are healthy `in_the_style_of`
    a given person or character.

    For example, if `in_the_style_of` is "Hagrid (Harry Potter)",
    > "Bloody hell, I haven't felt this good since Dumbledore gave me a dragon egg!"
    """
