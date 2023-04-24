import asyncio
import functools
import inspect

import pendulum

from marvin.ai_functions import ai_fn
from marvin.bot.response_formatters import RRuleFormatter


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


@ai_fn(include_date_in_prompt=False, response_format=RRuleFormatter())
def rrule(text: str) -> str:
    """
    Write an RRULE (RFC 5545) that represents the provided `text`.

    Do not reference specific dates or EXDATE unless the `text` explicitly says
    to. For example:

    # no specifc dates...

    "Every day at 9am except Wednesday" -> RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0;BYSECOND=0;BYDAY=MO,TU,TH,FR,SA,SU

    "Every week on Monday for 5 weeks" -> RRULE:FREQ=WEEKLY;COUNT=5;BYDAY=MO;BYHOUR=0;BYMINUTE=0;BYSECOND=0

    "Every 3 hours on Thursdays except 12pm" -> RRULE:FREQ=WEEKLY;INTERVAL=3;BYDAY=TH;BYHOUR=0,3,6,9,15,18,21;BYMINUTE=0;BYSECOND=0

    # if today's date is April 22, 2023

    "Every day at 9am except tomorrow" -> RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0;BYSECOND=0\nEXDATE:20230423T130000Z

    "Every week on Monday until May 31" -> RRULE:FREQ=WEEKLY;UNTIL=20230531T000000Z;BYDAY=MO;BYHOUR=0;BYMINUTE=0;BYSECOND=0

    """  # noqa: E501
    # yield the current date and time to help with relative dates
    yield pendulum.now().format("dddd, MMMM D, YYYY HH:mm ZZ")
