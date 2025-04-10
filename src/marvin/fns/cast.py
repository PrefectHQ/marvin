"""
Cast is a function that uses a language model to analyze the input data and transform it
into the specified target type, maintaining as much semantic meaning as possible.
"""

from typing import Any, TypeVar

import marvin
from marvin.agents.agent import Agent
from marvin.thread import Thread
from marvin.utilities.asyncio import run_sync
from marvin.utilities.types import TargetType

T = TypeVar("T")

PROMPT = """
You are an expert data converter that always maintains as much semantic
meaning as possible. You use inference or deduction whenever necessary to
understand and transform the input data. Examine the provided `data`, text,
or information and transform it into a single entity of the requested type.

- When providing integers, do not write out any decimals at all
- Use deduction where appropriate e.g. "3 dollars fifty cents" should be
    converted to 3.5 when casting to a float
- Preserve as much of the original meaning and structure as possible while
    conforming to the target type
- When providing a string response, do not return JSON or a quoted string
    unless they provided instructions requiring it. If you do return JSON, it
    must be valid and parseable including double quotes.
- When converting to bool, treat "truthy" values as true"""


async def cast_async(
    data: Any,
    target: TargetType[T] | None = None,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> T:
    """Asynchronously transforms input data into a specific type using a language model.

    This function uses a language model to analyze the input data and transform it
    into the specified target type, maintaining as much semantic meaning as possible.

    Args:
        data: The input data to transform. Can be any type.
        target: The type to transform the data into. Defaults to str.
        instructions: Optional additional instructions to guide the transformation.
            Used to provide specific guidance about how to interpret or transform
            the data.
        agent: Optional custom agent to use for transformation. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.
        context: Optional dictionary of additional context to include in the task.

    Returns:
        The transformed data of type T.

    Examples:
        ```python
        from marvin import cast_async
        await cast_async("whats the answer to it all?, int) # 42

        await cast_async("three point five", float, instructions="Convert words to numbers") # 3.5

        await cast_async("yes", bool) # True
        ```

    """
    if target is None:
        target = str

    if target is str and instructions is None:
        raise ValueError("Instructions are required when casting to string values.")

    task_context = context or {}
    task_context["Data to transform"] = data
    prompt = PROMPT
    if instructions:
        prompt += f"\n\nYou must follow these instructions for your transformation:\n{instructions}"

    task = marvin.Task[target](
        name="Cast Task",
        instructions=prompt,
        context=task_context,
        result_type=target,
        agents=[agent] if agent else None,
    )

    return await task.run_async(thread=thread)


def cast(
    data: Any,
    target: TargetType[T] | None = None,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> T:
    """Transforms input data into a specific type using a language model.

    This function uses a language model to analyze the input data and transform it
    into the specified target type, maintaining as much semantic meaning as possible.

    Args:
        data: The input data to transform. Can be any type.
        target: The type to transform the data into. Defaults to str.
        instructions: Optional additional instructions to guide the transformation.
            Used to provide specific guidance about how to interpret or transform
            the data.
        agent: Optional custom agent to use for transformation. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.
        context: Optional dictionary of additional context to include in the task.

    Returns:
        The transformed data of type T.

    Examples:
        ```python
        from marvin import cast
        cast(123, str) # '123'

        cast("three point five", float, instructions="Convert words to numbers") # 3.5

        cast("yes", bool) # True
        ```

    """
    return run_sync(
        cast_async(
            data=data,
            target=target,
            instructions=instructions,
            agent=agent,
            thread=thread,
            context=context,
        ),
    )
