"""Module for testing utlities."""

from typing import Any, Optional

from pydantic import BaseModel, Field

import marvin


class Assertion(BaseModel):
    is_equal: bool
    explanation: Optional[str] = Field(
        default=None,
        description=(
            "If unequal, a brief explanation of why the assertion failed. Not provided"
            " if equal."
        ),
    )


def assert_equal(llm_output: Any, expected: Any) -> bool:
    result = _assert_equal(llm_output, expected)
    assert (
        result.is_equal
    ), f"{result.explanation}\n>> LLM Output: {llm_output}\n>> Expected: {expected}"


@marvin.fn(model_kwargs=dict(model="gpt-4-1106-preview"))
def _assert_equal(llm_output: Any, expected: Any) -> Assertion:
    """
    An LLM generated the provided output as part of a unit test. Assert whether
    or not it meets the expectations of the test, which may be provided as
    either a string explanation or one or more valid examples. If
    """
