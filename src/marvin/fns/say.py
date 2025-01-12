import marvin
from marvin.agents.agent import Agent
from marvin.engine.thread import Thread, get_thread
from marvin.utilities.asyncio import run_sync


async def say_async(
    message: str,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
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

    Returns:
        str: The assistant's response to the user's message.
    """
    context = {}
    if instructions:
        context["Additional instructions"] = instructions

    with get_thread(thread) as thread:
        thread.add_user_message(message)
        task = marvin.Task[str](
            name="Response",
            instructions="Respond to the user",
            context=context,
            result_type=str,
            agent=agent,
        )

        return await task.run_async(thread=thread, handlers=[])


def say(
    message: str,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
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

    Returns:
        str: The assistant's response to the user's message.
    """
    return run_sync(
        say_async(
            message=message,
            instructions=instructions,
            agent=agent,
            thread=thread,
        ),
    )
