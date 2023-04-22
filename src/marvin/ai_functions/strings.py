import asyncio
import functools
import inspect

from marvin.ai_functions import ai_fn


def _strip_result(fn):
    """
    A decorator that automatically strips whitespace from the result of
    calling the function
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        if inspect.iscoroutine(result):
            result = asyncio.run(result)
        return result.strip()

    return wrapper


@_strip_result
@ai_fn
def fix_capitalization(text: str) -> str:
    """
    Given `text`, which represents complete sentences, fix any capitalization
    errors.
    """


@_strip_result
@ai_fn
def title_case(text: str) -> str:
    """
    Given `text`, change the case to make it APA style guide title case.
    """
