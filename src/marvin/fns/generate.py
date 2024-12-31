from typing import Optional, TypeVar

import marvin
from marvin.agents.agent import Agent
from marvin.engine.thread import Thread

T = TypeVar("T")

PROMPT = """
You are an expert data generator that always creates high-quality, random
examples of a description or type. The data you produce is relied on for
testing, examples, demonstrations, and more. You use inference or deduction
whenever necessary to supply missing or omitted data. You will be given
instructions or a type format, as well as a number of entities to generate. 

Unless the user explicitly says otherwise, assume they are request a VARIED and
REALISTIC selection of useful outputs that meet their criteria. However, you
should prefer common responses to uncommon ones.

If the user provides additional instructions or a description, assume they are
looking for examples that satisfy the description. Do not provide more
information than the user requests. For example, if they ask for various
technologies, give their names but do not explain what each technology is.
"""


def generate(
    target: type[T],
    n: int = 1,
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> list[T]:
    """
    Generates examples of a specific type or matching a description.

    This function uses a language model to generate high-quality, random examples
    that match the specified type or description. The examples are returned as a
    list.

    Args:
        target: The type of entities to generate.
        n: The number of examples to generate. Defaults to 1.
        instructions: Optional instructions describing what to generate. Used to
            provide specific guidance about what kinds of examples to create.
        agent: Optional custom agent to use for generation. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.

    Returns:
        A list of n generated entities of type T.
    """
    if target is str and instructions is None:
        raise ValueError("Instructions are required when target type is str.")

    task = marvin.Task(
        name="Generation Task",
        instructions=PROMPT,
        context={"Number to generate": n},
        result_type=list[target],
        agent=agent,
    )

    with marvin.instructions(instructions):
        return task.run(thread=thread)


async def generate_async(
    target: type[T],
    n: int = 1,
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> list[T]:
    """
    Generates examples of a specific type or matching a description asynchronously.

    This function uses a language model to generate high-quality, random examples
    that match the specified type or description. The examples are returned as a
    list.

    Args:
        target: The type of entities to generate.
        n: The number of examples to generate. Defaults to 1.
        instructions: Optional instructions describing what to generate. Used to
            provide specific guidance about what kinds of examples to create.
        agent: Optional custom agent to use for generation. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.

    Returns:
        A list of n generated entities of type T.
    """
    task = marvin.Task(
        name="Generation Task",
        instructions=PROMPT,
        context={"Number to generate": n},
        result_type=list[target],
        agent=agent,
    )

    with marvin.instructions(instructions):
        return await task.run_async(thread=thread)
