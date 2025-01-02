"""
Tasks for Marvin.

A Task is a container for a prompt and its associated state.
"""

import enum
import inspect
import uuid
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    TypeVar,
)

import marvin
from marvin.agents.actor import Actor
from marvin.agents.agent import Agent
from marvin.engine.thread import Thread
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.utilities.asyncio import run_sync
from marvin.utilities.types import Labels, as_classifier, is_classifier

T = TypeVar("T")

DEFAULT_PROMPT_TEMPLATE = inspect.cleandoc(
    """
    <id>{{task.id}}</id>
    {% if task.name %}
    <name>{{task.name}}</name>
    {% endif %}
    <instructions>{{task.instructions}}</instructions>
    {% if task.context %}
    <context>{{task.context}}</context>
    {% endif %}
    <result-type>{{task.result_type}}</result-type>
    <state>{{task.state}}</state>
    {% if task.parent %}
    <parent-task-id>{{task.parent.id}}</parent-task-id>
    {% endif %}
"""
)


class TaskState(str, enum.Enum):
    """State of a task."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESSFUL = "successful"
    FAILED = "failed"


@dataclass(kw_only=True)
class Task(Generic[T]):
    """A task is a container for a prompt and its associated state."""

    instructions: str = field(
        metadata={"description": "Instructions for the task"}, kw_only=False
    )

    result_type: type[T] | Labels = field(
        default=str,
        metadata={
            "description": "The expected type of the result. This can be a type or None if no result is expected."
        },
        kw_only=False,
    )

    id: uuid.UUID = field(
        default_factory=uuid.uuid4,
        metadata={"description": "Unique identifier for this task"},
        init=False,
    )

    prompt_template: Optional[str] = field(
        default=None,
        metadata={
            "description": "Optional Jinja template for customizing how the task appears in prompts. Will be rendered with a `task` variable containing this task instance."
        },
    )

    agent: Optional[Actor] = field(
        default=None,
        metadata={"description": "Optional agent or team to execute this task"},
    )

    context: dict[str, Any] = field(
        default_factory=dict, metadata={"description": "Context for the task"}
    )

    name: Optional[str] = field(
        default=None, metadata={"description": "Optional name for this task"}
    )

    tools: list[Callable[..., Any]] = field(
        default_factory=list,
        metadata={
            "description": "Tools to make available to any agents assigned to this task"
        },
    )

    memories: list[Memory] = field(
        default_factory=list,
        metadata={
            "description": "Memories to make available to any agents assigned to this task"
        },
    )

    state: TaskState = field(
        default=TaskState.PENDING,
        metadata={"description": "Current state of the task"},
        init=False,
    )

    result_validator: Optional[Callable[..., Any]] = field(
        default=None,
        metadata={
            "description": "Optional function that validates the result. Takes the raw result and returns a validated result or raises an error."
        },
    )

    report_state_change: bool = field(
        default=True,
        metadata={
            "description": "Whether to report the state change of this task to the thread."
        },
    )

    parent: Optional["Task[T]"] = field(
        default=None, metadata={"description": "Optional parent task"}
    )

    _children: list["Task[T]"] = field(
        default_factory=list, metadata={"description": "List of child tasks"}
    )

    result: Optional[T | str] = field(
        default=None,
        metadata={
            "description": "The result of the task. Can be either the expected type T or an error string."
        },
        init=False,
    )

    def __post_init__(self):
        """Transform raw sequences into Labels for classification tasks.

        We convert two types of shorthands:
        1. Raw sequences like ["red", "blue"] -> Labels(values=["red", "blue"])
           for single-label classification
        2. Double-nested lists like [["red", "blue"]] -> Labels(values=["red", "blue"], many=True)
           for multi-label classification

        Other classifier types (Enum, Literal, list[Enum], list[Literal]) are left as-is
        and only converted to Labels when needed via as_classifier().

        Raises:
            ValueError: If an empty list or invalid nested list is provided
        """
        # Handle double-nested list shorthand for multi-label
        if (
            isinstance(self.result_type, list)
            and len(self.result_type) == 1
            and isinstance(self.result_type[0], (list, tuple, set))
        ):
            if not self.result_type[0]:
                raise ValueError(
                    "Empty nested list is not allowed for multi-label classification"
                )
            self.result_type = Labels(self.result_type[0], many=True)
        # Handle raw sequences for single-label
        elif isinstance(self.result_type, (list, tuple, set)):
            if not self.result_type:
                raise ValueError("Empty list is not allowed for classification")
            if isinstance(self.result_type, list) and any(
                isinstance(x, (list, tuple, set)) for x in self.result_type
            ):
                raise ValueError(
                    "Invalid nested list format - use [['a', 'b']] for multi-label"
                )
            self.result_type = Labels(self.result_type)

    def get_agent(self) -> Agent:
        """Retrieve the agent assigned to this task."""
        return self.agent or marvin.defaults.agent

    def get_tools(self) -> list[Callable[..., Any]]:
        """Get the tools assigned to this task."""
        return self.tools + [t for m in self.memories for t in m.get_tools()]

    def is_classifier(self) -> bool:
        """Return True if this task is a classification task."""
        return is_classifier(self.result_type)

    def get_result_type(self) -> type[T]:
        """Get the effective result type for this task.
        For classification tasks, returns the type that should be used
        for validation (e.g., int or list[int])."""
        if self.is_classifier():
            return as_classifier(self.result_type).get_type()
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
        if self.is_classifier():
            return as_classifier(self.result_type).validate(raw_result)

        return raw_result

    def get_prompt(self) -> str:
        """Get the rendered prompt for this task.

        Uses the task's prompt_template (or default if None) and renders it with
        this task instance as the `task` variable.
        """
        template = self.prompt_template or DEFAULT_PROMPT_TEMPLATE

        prompt = Template(template=template).render(task=self)

        if self.is_classifier() and not self.prompt_template:
            prompt += (
                f"\n\nRespond with the integer index(es) of the labels you're "
                f"choosing: {as_classifier(self.result_type).get_indexed_labels()}"
            )

        return prompt

    async def run_async(
        self,
        *,
        thread: Optional[Thread | str] = None,
        raise_on_failure: bool = True,
    ) -> T:
        orchestrator = marvin.engine.orchestrator.Orchestrator(
            tasks=[self], thread=thread
        )
        await orchestrator.run(raise_on_failure=raise_on_failure)
        return self.result

    def run(
        self,
        *,
        thread: Optional[Thread | str] = None,
        raise_on_failure: bool = True,
    ) -> T:
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
