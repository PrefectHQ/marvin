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
    """Classify the data into one of the labels."""

    task = marvin.Task(
        name="Classification Task",
        instructions=PROMPT,
        context={"Data to classify": data},
        result_type=Labels(labels, many=multi_label),
        agent=agent,
    )

    with marvin.instructions(instructions):
        return task.run(thread=thread)
