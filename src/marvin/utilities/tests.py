import asyncio
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any

import httpx

from marvin import ai_fn, get_logger
from marvin.programs.utilities import ApproximatelyEquivalent


def assert_status_code(response: httpx.Response, status_code: int):
    try:
        full_response = response.json()
    except Exception:
        full_response = response.text
    error_message = (
        f"assert {response.status_code} == {status_code}"
        f"\nFull response: {full_response}"
    )
    assert response.status_code == status_code, error_message


def assert_approx_equal(statement_1: str, statement_2: str):
    assert asyncio.run(ApproximatelyEquivalent().run(statement_1, statement_2))


@ai_fn()
def _assert_llm(output: Any, expectation: Any) -> bool:
    """
    This function is used to unit test LLM outputs. The LLM `output` is compared
    to an `expectation` of what the output is, contains, or represents. The
    function returns `true` if the output satisfies the expectation and `false`
    otherwise. The expectation does not need to be matched exactly. If the
    expectation and output are semantically the same, the function should return
    true.


    For example:
        assert_llm(5, "5") -> True
        assert_llm("Greetings, friend!", "Hello, how are you?") -> True
        assert_llm("Hello, friend!", "a greeting") -> True
        assert_llm("I'm good, thanks!", "Hello, how are you?") -> False
        assert_llm(["red", "orange"], "a list of colors") -> True
        assert_llm(["red", "house"], "a list of colors") -> False
    """


def assert_llm(output: str, expectation: Any):
    if not _assert_llm(output, expectation):
        raise AssertionError(
            f"Output {output} does not satisfy expectation {expectation}"
        )


@asynccontextmanager
async def timer():
    start_time = asyncio.get_running_loop().time()
    yield
    elapsed_time = asyncio.get_running_loop().time() - start_time
    get_logger("timer").info(f"{elapsed_time:.5f} seconds elapsed")


def time_it(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with timer():
            result = await func(*args, **kwargs)
        return result

    return wrapper
