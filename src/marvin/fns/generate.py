from typing import Any, TypeVar, cast

import marvin
from marvin.agents.agent import Agent
from marvin.thread import Thread
from marvin.utilities.asyncio import run_sync
from marvin.utilities.types import TargetType

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


async def generate_async(
    target: TargetType[T] = str,
    n: int = 1,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
) -> list[T]:
    """Generates examples of a specific type or matching a description asynchronously.

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

    context: dict[str, Any] = {"Number to generate": n}
    if instructions:
        context["Additional instructions"] = instructions

    task = marvin.Task[list[target]](
        name="Generation Task",
        instructions=PROMPT,
        context=context,
        result_type=list[target],
        agents=[agent] if agent else None,
    )

    return cast(list[T], await task.run_async(thread=thread, handlers=[]))


def generate(
    target: TargetType[T] = str,
    n: int = 1,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
) -> list[T]:
    """Generates examples of a specific type or matching a description.

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
    return run_sync(
        generate_async(
            target=target,
            n=n,
            instructions=instructions,
            agent=agent,
            thread=thread,
        ),
    )
