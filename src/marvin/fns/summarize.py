from typing import Any

import marvin
from marvin.agents.agent import Agent
from marvin.thread import Thread
from marvin.utilities.asyncio import run_sync

PROMPT = """
You are an expert summarizer that distills information into clear, concise summaries
while preserving the most important semantic meaning and key points. Examine the 
provided `data`, text, or information and create a summary that captures the essence
of the content.

Guidelines for summarization:
- Maintain objectivity and accuracy
- Preserve key facts, figures, and relationships
- Focus on the most important information
- Use clear, concise language
- Adapt tone and style to match the content type
- Ensure the summary stands alone as a coherent piece of text"""


async def summarize_async(
    data: Any,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict | None = None,
) -> str:
    """Asynchronously creates a summary of the input data using a language model.

    This function uses a language model to analyze the input data and create a
    concise summary that captures the key information and semantic meaning.

    Args:
        data: The input data to summarize. Can be any type.
        instructions: Optional additional instructions to guide the summarization.
            Used to provide specific guidance about what aspects to focus on or
            how to structure the summary.
        agent: Optional custom agent to use for summarization. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.
        context: Optional dictionary of additional context to include in the task.

    Returns:
        A string containing the generated summary.

    Examples:
        >>> # Basic summarization
        >>> await summarize_async("Long article about climate change...")
        'Key findings on climate impacts...'

        >>> # Summarize with specific instructions
        >>> await summarize_async("Technical documentation...", instructions="Focus on API changes")
        'Major API updates include...'

    """
    task_context = context or {}
    task_context["Data to summarize"] = data
    prompt = PROMPT
    if instructions:
        prompt += (
            f"\n\nYou must follow these instructions for your summary:\n{instructions}"
        )

    task = marvin.Task[str](
        name="Summarize Task",
        instructions=prompt,
        context=task_context,
        result_type=str,
        agents=[agent] if agent else None,
    )

    return await task.run_async(thread=thread)


def summarize(
    data: Any,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict | None = None,
) -> str:
    """Creates a summary of the input data using a language model.

    This function uses a language model to analyze the input data and create a
    concise summary that captures the key information and semantic meaning.

    Args:
        data: The input data to summarize. Can be any type.
        instructions: Optional additional instructions to guide the summarization.
            Used to provide specific guidance about what aspects to focus on or
            how to structure the summary.
        agent: Optional custom agent to use for summarization. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.
        context: Optional dictionary of additional context to include in the task.

    Returns:
        A string containing the generated summary.

    Examples:
        >>> # Basic summarization
        >>> summarize("Long article about climate change...")
        'Key findings on climate impacts...'

        >>> # Summarize with specific instructions
        >>> summarize("Technical documentation...", instructions="Focus on API changes")
        'Major API updates include...'

    """
    return run_sync(
        summarize_async(
            data=data,
            instructions=instructions,
            agent=agent,
            thread=thread,
            context=context,
        ),
    )
