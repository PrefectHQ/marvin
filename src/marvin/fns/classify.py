import enum
from typing import Any, Literal, Optional, Sequence, TypeVar, Union, overload

import marvin
from marvin.agents.agent import Agent
from marvin.engine.thread import Thread
from marvin.utilities.asyncio import run_sync
from marvin.utilities.types import issubclass_safe

T = TypeVar("T")
E = TypeVar("E", bound=enum.Enum)

PROMPT = """
You are an expert classifier that always maintains as much semantic meaning
as possible when labeling text. You use inference or deduction whenever
necessary to understand missing or omitted data. Classify the provided `data`,
text, or information as one of the provided labels. For boolean labels,
consider "truthy" or affirmative inputs to be "true".
"""


@overload
async def classify_async(
    data: Any, labels: Sequence[T], multi_label: Literal[False] = False, **kwargs
) -> T: ...


@overload
async def classify_async(
    data: Any, labels: type[E], multi_label: Literal[False] = False, **kwargs
) -> E: ...


@overload
async def classify_async(
    data: Any, labels: Sequence[T], multi_label: Literal[True], **kwargs
) -> list[T]: ...


@overload
async def classify_async(
    data: Any, labels: type[E], multi_label: Literal[True], **kwargs
) -> list[E]: ...


async def classify_async(
    data: Any,
    labels: Union[Sequence[T], type[E]],
    multi_label: bool = False,
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> Union[T, E, list[T], list[E]]:
    """
    Asynchronously classifies input data into one or more predefined labels using a language model.

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
    """

    context = {"Data to classify": data}
    if instructions:
        context["Additional instructions"] = instructions

    # Convert Enum class to sequence of values if needed
    if issubclass_safe(labels, enum.Enum):
        label_values = [e.value for e in labels]
        result_type = labels  # Keep original enum type
    else:
        label_values = list(labels)
        result_type = label_values  # Keep original sequence

    # Handle multi-label by wrapping in a list
    if multi_label:
        result_type = [result_type]

    task = marvin.Task(
        name="Classification Task",
        instructions=PROMPT,
        context=context,
        result_type=result_type,
        agent=agent,
    )

    return await task.run_async(thread=thread)


@overload
def classify(
    data: Any, labels: Sequence[T], multi_label: Literal[False] = False, **kwargs
) -> T: ...


@overload
def classify(
    data: Any, labels: type[E], multi_label: Literal[False] = False, **kwargs
) -> E: ...


@overload
def classify(
    data: Any, labels: Sequence[T], multi_label: Literal[True], **kwargs
) -> list[T]: ...


@overload
def classify(
    data: Any, labels: type[E], multi_label: Literal[True], **kwargs
) -> list[E]: ...


def classify(
    data: Any,
    labels: Union[Sequence[T], type[E]],
    multi_label: bool = False,
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> Union[T, E, list[T], list[E]]:
    """
    Classifies input data into one or more predefined labels using a language model.

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
    """
    return run_sync(
        classify_async(
            data=data,
            labels=labels,
            multi_label=multi_label,
            instructions=instructions,
            agent=agent,
            thread=thread,
        )
    )
