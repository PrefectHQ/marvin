from typing import Any, Optional, TypeVar

import marvin
from marvin.agents.agent import Agent
from marvin.engine.thread import Thread

T = TypeVar("T")

PROMPT = """
You are an expert entity extractor that always maintains as much semantic
meaning as possible. You use inference or deduction whenever necessary to
supply missing or omitted data. Examine the provided `data`, text, or
information and generate a list of any entities or objects that match the
requested format.

- When providing integers, do not write out any decimals at all
- Use deduction where appropriate e.g. "3 dollars fifty cents" is a single
    value [3.5] not two values [3, 50] unless the user specifically asks for
    each part.
"""


def extract(
    data: Any,
    target: T = str,
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> list[T]:
    """
    Extracts entities of a specific type from the provided data.

    This function uses a language model to identify and extract entities of the
    specified type from the input data. The extracted entities are returned as a
    list.

    Args:
        data: The input data to extract entities from. Can be any type.
        target: The type of entities to extract. Defaults to str.
        instructions: Optional additional instructions to guide the extraction.
            Used to provide specific guidance about what to extract or how to
            process the data.
        agent: Optional custom agent to use for extraction. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.

    Returns:
        A list of extracted entities of type T.

    Note:
        *Either* a target type or instructions must be provided (or both).
        If only instructions are provided, the target type is assumed to be a
        string.
    """

    task = marvin.Task(
        name="Extraction Task",
        instructions=PROMPT,
        context={"Data to extract": data},
        result_type=list[target],
        agent=agent,
    )

    with marvin.instructions(instructions):
        return task.run(thread=thread)


async def extract_async(
    data: Any,
    target: T = str,
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> list[T]:
    """
    Extracts entities of a specific type from the provided data asynchronously.

    This function uses a language model to identify and extract entities of the
    specified type from the input data. The extracted entities are returned as a
    list.

    Args:
        data: The input data to extract entities from. Can be any type.
        target: The type of entities to extract. Defaults to str.
        instructions: Optional additional instructions to guide the extraction.
            Used to provide specific guidance about what to extract or how to
            process the data.
        agent: Optional custom agent to use for extraction. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.

    Returns:
        A list of extracted entities of type T.

    Note:
        *Either* a target type or instructions must be provided (or both).
        If only instructions are provided, the target type is assumed to be a
        string.
    """

    task = marvin.Task(
        name="Extraction Task",
        instructions=PROMPT,
        context={"Data to extract": data},
        result_type=list[target],
        agent=agent,
    )

    with marvin.instructions(instructions):
        return await task.run_async(thread=thread)
