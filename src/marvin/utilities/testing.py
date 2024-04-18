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


def assert_equal(
    llm_output: Any, expected: Any, instructions: str = None, model: str = None
) -> bool:
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

    model_kwargs = {}
    if model is not None:
        model_kwargs.update(model=model)

    result = _assert_equal(
        llm_output,
        expected,
        instructions=instructions,
        _model_kwargs=model_kwargs,
    )
    assert_msg = (
        f"{result.explanation}\n" f">> Instructions: {instructions}\n"
        if instructions
        else "" f">> LLM Output: {llm_output}\n" f">> Expected: {expected}"
    )
    assert result.is_equal, assert_msg


@marvin.fn(model_kwargs=dict(model="gpt-4-1106-preview"))
def _assert_equal(
    llm_output: Any, expected: Any, instructions: str = None
) -> Assertion:
    """
    An LLM generated the provided output as part of a unit test. Assert whether
    or not it meets the expectations of the test, which may be provided as
    either a string explanation or one or more valid examples or expected
    outputs. If instructions are provided, use them to compare the output to the
    expectation.
    """
