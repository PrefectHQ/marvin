import inspect
from typing import Any, TypeVar, cast

from pydantic import conlist

import marvin
from marvin.agents.agent import Agent
from marvin.thread import Thread
from marvin.utilities.asyncio import run_sync
from marvin.utilities.jinja import jinja_env
from marvin.utilities.jsonschema import JSONSchema
from marvin.utilities.types import TargetType

T = TypeVar("T")


async def generate_async(
    target: TargetType[T] = str,
    n: int = 1,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
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

    Returns:
        A list of n generated entities of type T.

    """
    if target is str and instructions is None:
        raise ValueError("Instructions are required when target type is str.")

    task_context = context or {}
    task_context["Number to generate"] = n

    prompt = """
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
    if instructions:
        prompt += f"\n\nYou must follow these instructions for your generation:\n{instructions}"

    task = marvin.Task[list[target]](
        name="Generation Task",
        instructions=prompt,
        context=task_context,
        result_type=conlist(target, min_length=n, max_length=n),
        agents=[agent] if agent else None,
    )

    return cast(list[T], await task.run_async(thread=thread))


def generate(
    target: TargetType[T] = str,
    n: int = 1,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
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
        ),
    )


async def generate_schema_async(
    instructions: str,
    base_schema: JSONSchema | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> JSONSchema:
    """Generates a JSON schema from a description."""

    prompt = inspect.cleandoc("""
        Your job is to generate JSON Schemas that match the user's instructions. The latest instruction is:
        
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

    return await task.run_async(thread=thread)


def generate_schema(
    instructions: str,
    base_schema: JSONSchema | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> JSONSchema:
    """Generates a JSON schema from a description."""
    return run_sync(
        generate_schema_async(
            instructions=instructions,
            base_schema=base_schema,
            agent=agent,
            thread=thread,
            context=context,
        )
    )
