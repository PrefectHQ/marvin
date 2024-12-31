"""
Tasks for Marvin.

A Task is a container for a prompt and its associated state.
"""

import enum
import uuid
from dataclasses import field
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    TypeVar,
)

import marvin
from marvin.agents.agent import Agent
from marvin.engine.thread import Thread
from marvin.utilities.asyncio import run_sync
from marvin.utilities.types import AutoDataClass

T = TypeVar("T")


class TaskState(str, enum.Enum):
    """State of a task."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESSFUL = "successful"
    FAILED = "failed"


class Task(Generic[T], AutoDataClass):
    """A task is a container for a prompt and its associated state."""

    _dataclass_config = {"kw_only": True}

    instructions: str = field(
        metadata={"description": "Instructions for the task"}, kw_only=False
    )

    result_type: type[T] = field(
        default=str,
        metadata={
            "description": "The expected type of the result. This can be a type or None if no result is expected."
        },
    )

    id: uuid.UUID = field(
        default_factory=uuid.uuid4,
        metadata={"description": "Unique identifier for this task"},
    )

    agent: Optional[Agent] = field(
        default=None, metadata={"description": "Optional agent to execute this task"}
    )

    context: dict[str, Any] = field(
        default_factory=dict, metadata={"description": "Context for the task"}
    )

    name: Optional[str] = field(
        default=None, metadata={"description": "Optional name for this task"}
    )

    state: TaskState = field(
        default=TaskState.PENDING, metadata={"description": "Current state of the task"}
    )

    result_validator: Optional[Callable] = field(
        default=None,
        metadata={
            "description": "Optional function that validates the result. Takes the raw result and returns a validated result or raises an error."
        },
    )

    parent: Optional["Task"] = field(
        default=None, metadata={"description": "Optional parent task"}
    )

    _children: list["Task"] = field(
        default_factory=list, metadata={"description": "List of child tasks"}
    )

    result: Optional[T | str] = field(
        default=None,
        metadata={
            "description": "The result of the task. Can be either the expected type T or an error string."
        },
    )

    def __post_init__(self):
        # Convert list result_type to Enum for convenience
        if isinstance(self.result_type, (list, tuple)):
            from marvin.utilities.types import create_enum

            self.result_type = create_enum(self.result_type)

    def get_agent(self) -> Agent:
        return self.agent or marvin.defaults.agent

    def _is_classifier(self) -> bool:
        """Return True if this task is a classification task."""
        from marvin.utilities.types import is_classifier

        return is_classifier(self.result_type)

    def get_result_type(self) -> type[T]:
        """Get the effective result type for this task.
        For classification tasks, returns the type that should be used
        for validation (e.g., int or list[int])."""
        from marvin.utilities.types import get_classifier_type

        if self._is_classifier():
            return get_classifier_type(self.result_type)
        return self.result_type

    def validate_result(self, raw_result: Any) -> T:
        """Validate a result against the expected type and custom validator."""
        # Apply custom validation if provided
        if self.result_validator is not None:
            try:
                return self.result_validator(raw_result)
            except Exception as e:
                raise ValueError(f"Error validating task result: {e}")

        # Handle classification types
        if self._is_classifier():
            from typing import get_origin

            from marvin.utilities.types import get_classifier_type, get_labels

            labels = get_labels(self.result_type)
            if not labels:
                raise ValueError("Invalid classification type")

            expected_type = get_classifier_type(self.result_type)
            if get_origin(expected_type) is list:
                if not isinstance(raw_result, (list, tuple)):
                    raise ValueError(
                        f"Expected a list of indices for multi-label classification, got {type(raw_result)}"
                    )
                if not all(isinstance(i, int) for i in raw_result):
                    raise ValueError("All elements must be integers")
                if not all(0 <= i < len(labels) for i in raw_result):
                    raise ValueError(
                        f"All indices must be between 0 and {len(labels)-1}"
                    )
                return [labels[i] for i in raw_result]
            else:
                if not isinstance(raw_result, int):
                    raise ValueError(
                        f"Expected an integer index for classification, got {type(raw_result)}"
                    )
                if not (0 <= raw_result < len(labels)):
                    raise ValueError(
                        f"Invalid index {raw_result}. Must be between 0 and {len(labels)-1}"
                    )
                return labels[raw_result]

        return raw_result

    async def run_async(
        self,
        *,
        thread: Optional[Thread | str] = None,
        raise_on_failure: bool = True,
    ):
        orchestrator = marvin.engine.Orchestrator(tasks=[self], thread=thread)
        await orchestrator.run(raise_on_failure=raise_on_failure)
        return self.result

    def run(
        self, *, thread: Optional[Thread | str] = None, raise_on_failure: bool = True
    ):
        return run_sync(
            self.run_async(thread=thread, raise_on_failure=raise_on_failure)
        )

    def mark_successful(self, result: T = None) -> None:
        """Mark the task as successful with an optional result."""
        self.result = self.validate_result(result)
        self.state = TaskState.SUCCESSFUL

    def mark_failed(self, error: str) -> None:
        """Mark the task as failed with an error message."""
        self.result = error
        self.state = TaskState.FAILED

    def mark_running(self) -> None:
        """Mark the task as running."""
        self.state = TaskState.RUNNING

    def is_pending(self) -> bool:
        """Check if the task is pending."""
        return self.state == TaskState.PENDING

    def is_running(self) -> bool:
        """Check if the task is running."""
        return self.state == TaskState.RUNNING

    def is_successful(self) -> bool:
        """Check if the task is successful."""
        return self.state == TaskState.SUCCESSFUL

    def is_failed(self) -> bool:
        """Check if the task is failed."""
        return self.state == TaskState.FAILED

    def is_incomplete(self) -> bool:
        """Check if the task is incomplete."""
        return self.state in (TaskState.PENDING, TaskState.RUNNING)

    def is_complete(self) -> bool:
        """Check if the task is complete."""
        return self.state in (TaskState.SUCCESSFUL, TaskState.FAILED)
