import inspect
from typing import Any, TypeVar, cast

from pydantic import conlist

import marvin
from marvin.agents.agent import Agent
from marvin.handlers.handlers import AsyncHandler, Handler
from marvin.thread import Thread
from marvin.utilities.asyncio import run_sync
from marvin.utilities.jinja import jinja_env
from marvin.utilities.jsonschema import JSONSchema
from marvin.utilities.types import TargetType

T = TypeVar("T")


DEFAULT_PROMPT = """
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
    target: TargetType[T] | None = None,
    n: int = 1,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
    handlers: list[Handler | AsyncHandler] | None = None,
    prompt: str | None = None,
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
        context: Optional dictionary of additional context to include in the task.
        handlers: Optional list of handlers to use for the task.
        prompt: Optional prompt to use for the task. If not provided, the default
            prompt will be used.
    Returns:
        A list of n generated entities of type T.

    """
    _target = target

    if target is None:
        _target = str

    if _target is str and instructions is None:
        raise ValueError("Instructions are required when generating string values.")

    task_context = context or {}
    task_context["Number to generate"] = n

    prompt = prompt or DEFAULT_PROMPT
    if instructions:
        prompt += f"\n\nYou must follow these instructions for your generation:\n{instructions}"

    task = marvin.Task[list[target]](
        name="Generation Task",
        instructions=prompt,
        context=task_context,
        result_type=conlist(_target, min_length=n, max_length=n),
        agents=[agent] if agent else None,
    )

    return cast(list[T], await task.run_async(thread=thread, handlers=handlers))


def generate(
    target: TargetType[T] | None = None,
    n: int = 1,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
    handlers: list[Handler | AsyncHandler] | None = None,
    prompt: str | None = None,
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
        context: Optional dictionary of additional context to include in the task.
        handlers: Optional list of handlers to use for the task.
        prompt: Optional prompt to use for the task. If not provided, the default
            prompt will be used.
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
            context=context,
            handlers=handlers,
            prompt=prompt,
        ),
    )


async def generate_schema_async(
    instructions: str,
    base_schema: JSONSchema | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
    handlers: list[Handler | AsyncHandler] | None = None,
    prompt: str | None = None,
) -> JSONSchema:
    """Generates a JSON schema from a description."""

    prompt = prompt or inspect.cleandoc("""
        Your job is to generate JSON schemas that match the user's instructions. The latest instruction is:
        
        <instructions>
        {{instructions}}
        </instructions>
        
        ---
        {% if base_schema %}
        Base your response on the following schema as much as possible:
        <base_schema>
        {{ base_schema }}
        </base_schema>
        {% else %}
        Base your response on previous instructions if possible.
        {% endif %}
        
        """)

    task = marvin.Task[JSONSchema](
        name="JSONSchema Generation",
        instructions=jinja_env.from_string(prompt).render(
            instructions=instructions,
            base_schema=base_schema,
        ),
        context=context,
        result_type=JSONSchema,
        agents=[agent] if agent else None,
    )

    return await task.run_async(thread=thread, handlers=handlers)


def generate_schema(
    instructions: str,
    base_schema: JSONSchema | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
    handlers: list[Handler | AsyncHandler] | None = None,
    prompt: str | None = None,
) -> JSONSchema:
    """Generates a JSON schema from a description."""
    return run_sync(
        generate_schema_async(
            instructions=instructions,
            base_schema=base_schema,
            agent=agent,
            thread=thread,
            context=context,
            handlers=handlers,
            prompt=prompt,
        )
    )
