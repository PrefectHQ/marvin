import asyncio
from contextlib import asynccontextmanager
from functools import wraps

import httpx

from marvin import get_logger
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
