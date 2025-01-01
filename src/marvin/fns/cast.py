from typing import Any, Optional, TypeVar

import marvin
from marvin.agents.agent import Agent
from marvin.engine.thread import Thread
from marvin.utilities.asyncio import run_sync

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
- When converting to bool, treat "truthy" values as true

"""


async def cast_async(
    data: Any,
    target: type[T] = str,
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> T:
    """
    Converts input data into a single entity of the specified target type asynchronously.

    This function uses a language model to analyze the input data and convert
    it into a single entity of the specified type, preserving semantic meaning
    where possible.

    Args:
        data: The input data to convert. Can be any type.
        target: The type to convert the data into. Defaults to str.
        instructions: Optional additional instructions to guide the conversion.
            Used to provide specific guidance about how to interpret or
            transform the data. Required when target is str.
        agent: Optional custom agent to use for conversion. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.

    Returns:
        A single entity of type T.

    Raises:
        ValueError: If target is str and no instructions are provided.
    """
    if target is str and instructions is None:
        raise ValueError("Instructions are required when target type is str.")

    context = {"Data to transform": data}
    if instructions:
        context["Additional instructions"] = instructions

    task = marvin.Task(
        name="Cast Task",
        instructions=PROMPT,
        context=context,
        result_type=target,
        agent=agent,
    )

    return await task.run_async(thread=thread)


def cast(
    data: Any,
    target: type[T] = str,
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> T:
    """
    Converts input data into a single entity of the specified target type.

    This function uses a language model to analyze the input data and convert
    it into a single entity of the specified type, preserving semantic meaning
    where possible.

    Args:
        data: The input data to convert. Can be any type.
        target: The type to convert the data into. Defaults to str.
        instructions: Optional additional instructions to guide the conversion.
            Used to provide specific guidance about how to interpret or
            transform the data. Required when target is str.
        agent: Optional custom agent to use for conversion. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.

    Returns:
        A single entity of type T.

    Raises:
        ValueError: If target is str and no instructions are provided.
    """
    return run_sync(
        cast_async(
            data=data,
            target=target,
            instructions=instructions,
            agent=agent,
            thread=thread,
        )
    )
