from typing import Any, TypeVar

import marvin
from marvin.agents.agent import Agent
from marvin.handlers.handlers import AsyncHandler, Handler
from marvin.thread import Thread
from marvin.utilities.asyncio import run_sync
from marvin.utilities.types import TargetType

T = TypeVar("T")

DEFAULT_PROMPT = """
You are an expert entity extractor that always maintains as much semantic
meaning as possible. You use inference or deduction whenever necessary to
supply missing or omitted data. Examine the provided `data`, text, or
information and generate a list of any entities or objects that match the
requested format.

- When providing integers, do not write out any decimals at all
- Use deduction where appropriate e.g. "3 dollars fifty cents" is a single
    value [3.5] not two values [3, 50] unless the user specifically asks for
    each part."""

PROMPT = DEFAULT_PROMPT  # for backwards compatibility


async def extract_async(
    data: Any,
    target: TargetType[T] | None = None,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
    handlers: list[Handler | AsyncHandler] | None = None,
    prompt: str | None = None,
) -> list[T]:
    """Extracts entities of a specific type from the provided data.

    This function uses a language model to identify and extract entities of the
    specified type from the input data. The extracted entities are returned as a
    list.

    Args:
        data: The input data to extract entities from. Can be any type.
        target: The type of entities to extract. Defaults to str.
        instructions: Optional additional instructions to guide the extraction.
            Used to provide specific guidance about what to extract or how to
            process the data. Required when target is str.
        agent: Optional custom agent to use for extraction. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.
        context: Optional dictionary of additional context to include in the task.
        handlers: Optional list of handlers to use for the task.
        prompt: Optional prompt to use for the task. If not provided, the default
            prompt will be used.
    Returns:
        A list of extracted entities of type T.

    Raises:
        ValueError: If target is str and no instructions are provided.

    """
    if target is None:
        target = str

    if target is str and instructions is None:
        raise ValueError("Instructions are required when extracting string values.")

    task_context = context or {}
    task_context["Data to extract"] = data
    prompt = prompt or PROMPT
    if instructions:
        prompt += f"\n\nYou must follow these instructions for your extraction:\n{instructions}"

    task = marvin.Task[list[target]](
        name="Extraction Task",
        instructions=prompt,
        context=task_context,
        result_type=list[target],
        agents=[agent] if agent else None,
    )

    return await task.run_async(thread=thread, handlers=handlers)


def extract(
    data: Any,
    target: TargetType[T] | None = None,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
    handlers: list[Handler | AsyncHandler] | None = None,
    prompt: str | None = None,
) -> list[T]:
    """Extracts entities of a specific type from the provided data.

    This function uses a language model to identify and extract entities of the
    specified type from the input data. The extracted entities are returned as a
    list.

    Args:
        data: The input data to extract entities from. Can be any type.
        target: The type of entities to extract. Defaults to str.
        instructions: Optional additional instructions to guide the extraction.
            Used to provide specific guidance about what to extract or how to
            process the data. Required when target is str.
        agent: Optional custom agent to use for extraction. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.
        context: Optional dictionary of additional context to include in the task.
        handlers: Optional list of handlers to use for the task.
        prompt: Optional prompt to use for the task. If not provided, the default
            prompt will be used.

    Returns:
        A list of extracted entities of type T.

    Raises:
        ValueError: If target is str and no instructions are provided.

    """
    return run_sync(
        extract_async(
            data=data,
            target=target,
            instructions=instructions,
            agent=agent,
            thread=thread,
            context=context,
            handlers=handlers,
            prompt=prompt,
        ),
    )
