import marvin


@marvin.fn(model_kwargs={"model": "gpt-3.5-turbo"})
async def describe_event_as_key(event_digest: str) -> str:
    """given an event digest, produce descriptive key in the following format:

    `about_{KEYWORD_1}_{KEYWORD_2}`

    where `KEYWORD_1` `KEYWORD_2` are the most semantically representative words
    of the event digest. the keywords need not be present in the event digest, only
    semantically representative.

    `about_` should be present in each key and the key should always be a total
    of 4 lowercase words separated by 2 underscores. e.g. `about_fixing_broken_imports`
    """
