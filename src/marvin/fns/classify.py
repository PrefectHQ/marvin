import enum
from collections.abc import Sequence
from typing import Any, Literal, TypeVar, overload

import marvin
from marvin.agents.agent import Agent
from marvin.thread import Thread
from marvin.utilities.asyncio import run_sync
from marvin.utilities.types import Labels, issubclass_safe

T = TypeVar("T")

PROMPT = """
You are an expert classifier that always maintains as much semantic meaning
as possible when labeling text. You use inference or deduction whenever
necessary to understand missing or omitted data. Classify the provided `data`,
text, or information as one of the provided labels. For boolean labels,
consider "truthy" or affirmative inputs to be "true"."""


@overload
async def classify_async(
    data: Any,
    labels: Sequence[T] | type[T],
    multi_label: Literal[False] = False,
    *,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> T: ...


@overload
async def classify_async(
    data: Any,
    labels: Sequence[T] | type[T],
    multi_label: Literal[True],
    *,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> list[T]: ...


@overload
async def classify_async(
    data: Any,
    labels: Sequence[T] | type[T],
    multi_label: bool = False,
    *,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> T | list[T]: ...


async def classify_async(
    data: Any,
    labels: Sequence[T] | type[T],
    multi_label: bool = False,
    *,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> T | list[T]:
    """Asynchronously classifies input data into one or more predefined labels using a language model.

    This function uses a language model to analyze the input data and assign it to
    the most appropriate label(s) from the provided sequence of labels or Enum class.

    Args:
        data: The input data to classify. Can be any type.
        labels: Either a sequence of possible labels (of type T) or an Enum class to
            classify the data into. If an Enum class is provided, its values will be
            used as the labels.
        multi_label: If False (default), returns a single label. If True, returns
            multiple labels as a list.
        instructions: Optional additional instructions to guide the classification.
            Used to provide specific guidance about how to interpret or classify
            the data.
        agent: Optional custom agent to use for classification. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.
        context: Optional dictionary of additional context to include in the task.

    Returns:
        - If labels is a Sequence[T]:
            - If multi_label is False: returns T
            - If multi_label is True: returns list[T]
        - If labels is an Enum class:
            - If multi_label is False: returns E (the Enum value)
            - If multi_label is True: returns list[E] (list of Enum values)

    Examples:
        >>> # Using a sequence of labels
        >>> await classify_async("red car", ["red", "blue", "green"])
        'red'

        >>> # Using an Enum class
        >>> class Colors(enum.Enum):
        ...     RED = "red"
        ...     BLUE = "blue"
        ...     GREEN = "green"
        >>> await classify_async("red car", Colors)
        <Colors.RED: 'red'>

        >>> # Multi-label classification
        >>> await classify_async("red and blue car", Colors, multi_label=True)
        [<Colors.RED: 'red'>, <Colors.BLUE: 'blue'>]

        >>> # Boolean classification
        >>> await classify_async("2+2=4", bool)
        True

    """
    task_context = context or {}
    task_context.update({"Data to classify": data})

    prompt = PROMPT
    if instructions:
        prompt += f"\n\nYou must follow these instructions for your classification:\n{instructions}"

    # Handle bool/enum types specially for correct typing
    if labels is bool or issubclass_safe(labels, enum.Enum):
        # For bool/enum, we need list[labels] for multi-label
        result_type = list[labels] if multi_label else labels  # Runtime type
        ReturnType = list[T] if multi_label else T  # Generic type
    else:
        # For sequences, we use Labels for runtime validation
        result_type = Labels(labels, many=multi_label)  # Runtime type
        ReturnType = list[T] if multi_label else T  # Generic type

    task = marvin.Task[ReturnType](
        name="Classification Task",
        instructions=prompt,
        context=task_context,
        result_type=result_type,
        agents=[agent] if agent else None,
    )

    return await task.run_async(thread=thread)


@overload
def classify(
    data: Any,
    labels: Sequence[T] | type[T],
    multi_label: Literal[False] = False,
    *,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> T: ...


@overload
def classify(
    data: Any,
    labels: Sequence[T] | type[T],
    multi_label: Literal[True],
    *,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> list[T]: ...


@overload
def classify(
    data: Any,
    labels: Sequence[T] | type[T],
    multi_label: bool = False,
    *,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> T | list[T]: ...


def classify(
    data: Any,
    labels: Sequence[T] | type[T],
    multi_label: bool = False,
    *,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
) -> T | list[T]:
    """Classifies input data into one or more predefined labels using a language model.

    This function uses a language model to analyze the input data and assign it to
    the most appropriate label(s) from the provided sequence of labels or Enum class.

    Args:
        data: The input data to classify. Can be any type.
        labels: Either a sequence of possible labels (of type T) or an Enum class to
            classify the data into. If an Enum class is provided, its values will be
            used as the labels.
        multi_label: If False (default), returns a single label. If True, returns
            multiple labels as a list.
        instructions: Optional additional instructions to guide the classification.
            Used to provide specific guidance about how to interpret or classify
            the data.
        agent: Optional custom agent to use for classification. If not provided,
            the default agent will be used.
        thread: Optional thread for maintaining conversation context. Can be
            either a Thread object or a string thread ID.
        context: Optional dictionary of additional context to include in the task.

    Returns:
        - If labels is a Sequence[T]:
            - If multi_label is False: returns T
            - If multi_label is True: returns list[T]
        - If labels is an Enum class:
            - If multi_label is False: returns E (the Enum value)
            - If multi_label is True: returns list[E] (list of Enum values)

    Examples:
        >>> # Using a sequence of labels
        >>> classify("red car", ["red", "blue", "green"])
        'red'

        >>> # Using an Enum class
        >>> class Colors(enum.Enum):
        ...     RED = "red"
        ...     BLUE = "blue"
        ...     GREEN = "green"
        >>> classify("red car", Colors)
        <Colors.RED: 'red'>

        >>> # Multi-label classification
        >>> classify("red and blue car", Colors, multi_label=True)
        [<Colors.RED: 'red'>, <Colors.BLUE: 'blue'>]

        >>> # Boolean classification
        >>> classify("2+2=4", bool)
        True

    """
    return run_sync(
        classify_async(
            data=data,
            labels=labels,
            multi_label=multi_label,
            instructions=instructions,
            agent=agent,
            thread=thread,
            context=context,
        ),
    )
