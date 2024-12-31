from typing import Any, Literal, Optional, Sequence, TypeVar, overload

import marvin
from marvin.agents.agent import Agent
from marvin.engine.thread import Thread
from marvin.utilities.types import Labels

T = TypeVar("T")

PROMPT = """
You are an expert classifier that always maintains as much semantic meaning
as possible when labeling text. You use inference or deduction whenever
necessary to understand missing or omitted data. Classify the provided `data`,
text, or information as one of the provided labels. For boolean labels,
consider "truthy" or affirmative inputs to be "true".
"""


@overload
def classify(
    data: Any, labels: Sequence[T], multi_label: Literal[False] = False, **kwargs
) -> T: ...


@overload
def classify(
    data: Any, labels: Sequence[T], multi_label: Literal[True], **kwargs
) -> list[T]: ...


def classify(
    data: Any,
    labels: Sequence[T],
    multi_label: bool = False,
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> T | list[T]:
    """
    Classifies input data into one or more predefined labels using a language model.

    This function uses a language model to analyze the input data and assign it to
    the most appropriate label(s) from the provided sequence of labels.

    Args:
        data: The input data to classify. Can be any type.
        labels: A sequence of possible labels (of type T) to classify the data into.
        multi_label: If False (default), returns a single label. If True, returns
            multiple labels as a list.
        instructions: Optional additional instructions to guide the classification.
            Used to provide specific guidance about how to interpret or classify
            the data.
        agent: Optional custom agent to use for classification. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.

    Returns:
        If multi_label is False, returns a single label of type T.
        If multi_label is True, returns a list of labels of type T.
    """

    context = {"Data to classify": data}
    if instructions:
        context["Additional instructions"] = instructions

    task = marvin.Task(
        name="Classification Task",
        instructions=PROMPT,
        context=context,
        result_type=Labels(labels, many=multi_label),
        agent=agent,
    )

    return task.run(thread=thread)


async def classify_async(
    data: Any,
    labels: Sequence[T],
    multi_label: bool = False,
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> T | list[T]:
    """
    Asynchronously classifies input data into one or more predefined labels using a language model.

    This function uses a language model to analyze the input data and assign it to
    the most appropriate label(s) from the provided sequence of labels.

    Args:
        data: The input data to classify. Can be any type.
        labels: A sequence of possible labels (of type T) to classify the data into.
        multi_label: If False (default), returns a single label. If True, returns
            multiple labels as a list.
        instructions: Optional additional instructions to guide the classification.
            Used to provide specific guidance about how to interpret or classify
            the data.
        agent: Optional custom agent to use for classification. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.

    Returns:
        If multi_label is False, returns a single label of type T.
        If multi_label is True, returns a list of labels of type T.
    """

    context = {"Data to classify": data}
    if instructions:
        context["Additional instructions"] = instructions

    task = marvin.Task(
        name="Classification Task",
        instructions=PROMPT,
        context=context,
        result_type=Labels(labels, many=multi_label),
        agent=agent,
    )

    return await task.run_async(thread=thread)
