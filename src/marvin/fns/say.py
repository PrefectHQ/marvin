from typing import Any, Sequence

from pydantic_ai.messages import UserContent

import marvin
from marvin.agents.actor import Actor
from marvin.handlers.handlers import AsyncHandler, Handler
from marvin.thread import Thread, get_thread
from marvin.utilities.asyncio import run_sync


async def say_async(
    message: str | Sequence[UserContent],
    instructions: str | None = None,
    agent: Actor | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
    handlers: list[Handler | AsyncHandler] | None = None,
) -> str:
    """Responds to a user message in a conversational way.

    This function uses a language model to process the user's message and generate
    an appropriate response, taking into account any specific instructions and
    maintaining conversation history through the thread.

    Args:
        message: The user's message to respond to.
        instructions: Optional additional instructions to guide the response.
            Used to provide specific guidance about how to interpret or
            respond to the message.
        agent: Optional custom agent to use for the response. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.
        context: Optional dictionary of additional context to include in the task.
        handlers: Optional list of handlers to use for the task.
    Returns:
        str: The assistant's response to the user's message.
    """
    task_context = context or {}
    if instructions:
        task_context["Additional instructions"] = instructions

    with get_thread(thread) as thread:
        await thread.add_user_message_async(message)
        task = marvin.Task[str](
            instructions="Respond to the user",
            context=task_context,
            result_type=str,
            agents=[agent] if agent else None,
        )

        return await task.run_async(thread=thread, handlers=handlers)


def say(
    message: str | Sequence[UserContent],
    instructions: str | None = None,
    agent: Actor | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
    handlers: list[Handler | AsyncHandler] | None = None,
) -> str:
    """Responds to a user message in a conversational way.

    This function uses a language model to process the user's message and generate
    an appropriate response, taking into account any specific instructions and
    maintaining conversation history through the thread.

    Args:
        message: The user's message to respond to.
        instructions: Optional additional instructions to guide the response.
            Used to provide specific guidance about how to interpret or
            respond to the message.
        agent: Optional custom agent to use for the response. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.
        context: Optional dictionary of additional context to include in the task.
        handlers: Optional list of handlers to use for the task.
    Returns:
        str: The assistant's response to the user's message.
    """
    return run_sync(
        say_async(
            message=message,
            instructions=instructions,
            agent=agent,
            thread=thread,
            context=context,
            handlers=handlers,
        ),
    )
