import asyncio

import httpx

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
