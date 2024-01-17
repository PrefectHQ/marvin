"""Utilities for running unit tests."""

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
    """
    Asserts whether the LLM output meets the expected output.

    This function uses an LLM to assess whether the provided output (llm_output)
    meets some expectation. It allows us to make semantic claims like "the output
    is a list of first names" to make assertions about stochastic LLM outputs.

    Args:
        llm_output (Any): The output from the LLM.
        expected (Any): The expected output.

    Returns:
        bool: True if the LLM output meets the expectation, False otherwise.

    Raises:
        AssertionError: If the LLM output does not meet the expectation.
    """

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
