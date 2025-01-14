"""Tasks for Marvin.

A Task is a container for a prompt and its associated state.
"""

import enum
import json
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    Optional,
    Sequence,
    TypeVar,
)

from pydantic import TypeAdapter

import marvin
from marvin.agents.actor import Actor
from marvin.agents.team import Swarm
from marvin.engine.thread import Thread
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.utilities.asyncio import run_sync
from marvin.utilities.types import Labels, as_classifier, is_classifier

if TYPE_CHECKING:
    from marvin.engine.handlers import AsyncHandler, Handler

T = TypeVar("T")

NOTSET = "__NOTSET__"

# Global context var for current task
_current_task: ContextVar[Optional["Task"]] = ContextVar(
    "current_task",
    default=None,
)

_type_adapters: dict[type[T], TypeAdapter[T]] = {}


def get_type_adapter(result_type: type[T]) -> TypeAdapter[T]:
    if result_type not in _type_adapters:
        _type_adapters[result_type] = TypeAdapter(result_type)
    return _type_adapters[result_type]


class TaskState(str, enum.Enum):
    """State of a task."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(kw_only=True, init=False)
class Task(Generic[T]):
    """A task is a container for a prompt and its associated state."""

    name: str | None = field(
        default=None,
        metadata={"description": "Optional name for this task"},
    )

    instructions: str = field(
        metadata={"description": "Instructions for the task"},
        kw_only=False,
    )

    result_type: type[T] | Labels = field(
        default=NOTSET,
        metadata={
            "description": "The expected type of the result. This can be a type or None if no result is expected. If not set, the result type will be str.",
        },
        kw_only=False,
    )

    id: str = field(
        default_factory=lambda: uuid.uuid4().hex[:8],
        metadata={"description": "Unique identifier for this task"},
        init=False,
        repr=False,
    )

    prompt_template: str | Path = field(
        default=Path("task.jinja"),
        metadata={
            "description": "Optional Jinja template for customizing how the task appears in prompts. Will be rendered with a `task` variable containing this task instance.",
        },
        repr=False,
    )

    agent: Actor | None = field(
        default=None,
        metadata={"description": "Optional agent or team assigned to this task"},
    )

    context: dict[str, Any] = field(
        default_factory=dict,
        metadata={"description": "Context for the task"},
    )

    tools: list[Callable[..., Any]] = field(
        default_factory=list,
        metadata={
            "description": "Tools to make available to any agents assigned to this task",
        },
    )

    memories: list[Memory] = field(
        default_factory=list,
        metadata={
            "description": "Memories to make available to any agents assigned to this task",
        },
    )

    state: TaskState = field(
        default=TaskState.PENDING,
        metadata={"description": "Current state of the task"},
        init=False,
    )

    result_validator: Callable[..., Any] | None = field(
        default=None,
        metadata={
            "description": "Optional function that validates the result. Takes the raw result and returns a validated result or raises an error.",
        },
        repr=False,
    )

    _parent: "Task | None" = field(
        default=None,
        metadata={"description": "Optional parent task"},
        init=False,
    )

    subtasks: set["Task"] = field(
        default_factory=set,
        metadata={
            "description": "List of subtasks, or tasks for which this task is the parent"
        },
        init=False,
        repr=False,
    )

    depends_on: set["Task"] = field(
        default_factory=set,
        metadata={
            "description": "List of tasks that must be completed before this task can be run"
        },
        repr=False,
    )

    result: T | str | None = field(
        default=None,
        metadata={
            "description": "The result of the task. Can be either the expected type T or an error string.",
        },
        init=False,
        repr=False,
    )

    allow_fail: bool = field(
        default=False,
        metadata={"description": "Whether to allow the task to fail"},
        repr=False,
    )
    allow_skip: bool = field(
        default=False,
        metadata={"description": "Whether to allow the task to skip"},
        repr=False,
    )

    cli: bool = field(
        default=False,
        metadata={
            "description": "If True, agents will be given a tool for interacting with users on the CLI.",
        },
    )

    # Add _tokens field for context management
    _tokens: list[Any] = field(default_factory=list, init=False, repr=False)

    def __init__(
        self,
        instructions: str,
        result_type: type[T] | Labels | Literal["__NOTSET__"] = NOTSET,
        *,
        name: str | None = None,
        prompt_template: str | Path = Path("task.jinja"),
        agents: list[Actor] | None = None,
        context: dict[str, Any] | None = None,
        tools: list[Callable[..., Any]] | None = None,
        memories: list[Memory] | None = None,
        result_validator: Callable[..., Any] | None = None,
        parent: "Task[T] | None" = None,
        depends_on: Sequence["Task[T]"] | None = None,
        allow_fail: bool = False,
        allow_skip: bool = False,
        cli: bool = False,
    ) -> None:
        """Initialize a Task.

        Args:
            instructions: Instructions for the task
            name: Optional name for this task
            result_type: Expected type of the result
            prompt_template: Optional Jinja template for customizing task appearance
            agents: Optional list of agents to execute this task. If more than
                one agent or team is provided, they will automatically be combined
                into a team.
            context: Context for the task
            tools: Tools to make available to agents
            memories: Memories to make available to agents
            result_validator: Optional function to validate results
            parent: Optional parent task. If not provided and there is a current task
                in the context, that task will be used as the parent.
            allow_fail: Whether to allow the task to fail
            allow_skip: Whether to allow the task to skip
            cli: Whether to enable CLI interaction tools

        """
        # required fields
        self.instructions = instructions

        # optional fields with defaults
        self.name = name
        self.result_type = result_type if result_type is not NOTSET else str
        self.prompt_template = prompt_template
        self.context = context or {}
        self.tools = tools or []
        self.memories = memories or []
        self.result_validator = result_validator
        self.allow_fail = allow_fail
        self.allow_skip = allow_skip
        self.cli = cli

        # key fields
        self.id = uuid.uuid4().hex[:8]
        self.state = TaskState.PENDING
        self.result = None

        # if no parent is provided, use the current task from context
        self.parent = parent if parent is not None else _current_task.get()
        self.subtasks = set()
        self.depends_on = set(depends_on or [])

        # internal fields
        self._tokens = []

        # handle agents
        if agents:
            if len(agents) > 1:
                self.agent = Swarm(agents=agents)
            else:
                self.agent = agents[0]

        # Handle result type validation
        if isinstance(self.result_type, (list, tuple, set)):
            if len(self.result_type) == 1 and isinstance(
                self.result_type[0],
                (list, tuple, set),
            ):
                if not self.result_type[0]:
                    raise ValueError(
                        "Empty nested list is not allowed for multi-label classification",
                    )
                self.result_type = Labels(self.result_type[0], many=True)
            else:
                if not self.result_type:
                    raise ValueError("Empty list is not allowed for classification")
                if any(isinstance(x, (list, tuple, set)) for x in self.result_type):
                    raise ValueError(
                        "Invalid nested list format - use [['a', 'b']] for multi-label",
                    )
                self.result_type = Labels(self.result_type)

    def __hash__(self) -> int:
        return hash(self.id)

    def _validate_result_type(self) -> None:
        """Validates the result type by converting classification shorthand into
        Labels and ensuring that the result type is a valid type.

        Valid shorthand:
        - result_type = ["red", "blue"] -> Labels(values=["red", "blue"])
        - result_type = [["red", "blue"]] -> Labels(values=["red", "blue"], many=True)
        """
        # Handle double-nested list shorthand for multi-label
        if (
            isinstance(self.result_type, list)
            and len(self.result_type) == 1
            and isinstance(self.result_type[0], (list, tuple, set))
        ):
            if not self.result_type[0]:
                raise ValueError(
                    "Empty nested list is not allowed for multi-label classification",
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
                    "Invalid nested list format - use [['a', 'b']] for multi-label",
                )
            self.result_type = Labels(self.result_type)

    def friendly_name(self) -> str:
        """Get a friendly name for this task."""
        if self.name:
            return f'Task "{self.name}"'
        # Replace consecutive newlines with a single space
        instructions = " ".join(self.instructions.split())
        return f'Task {self.id} ("{instructions[:40]}...")'

    @property
    def parent(self) -> "Task | None":
        """Get the parent task of this task."""
        return self._parent

    @parent.setter
    def parent(self, value: "Task | None") -> None:
        """Set the parent task of this task."""
        if self._parent is not None:
            self._parent.subtasks.discard(self)
        self._parent = value
        if self._parent is not None:
            self._parent.subtasks.add(self)

    def get_agent(self) -> Actor:
        """Retrieve the agent assigned to this task."""
        return self.agent or marvin.defaults.agent

    def get_tools(self) -> list[Callable[..., Any]]:
        """Get the tools assigned to this task."""
        tools = []
        tools.extend(self.tools)
        tools.extend([t for m in self.memories for t in m.get_tools()])
        if self.cli:
            import marvin.tools.interactive.cli

            tools.append(marvin.tools.interactive.cli.cli)
        return tools

    def is_classifier(self) -> bool:
        """Return True if this task is a classification task."""
        return is_classifier(self.result_type)

    def get_result_type(self) -> type[T]:
        """Get the effective result type for this task.
        For classification tasks, returns the type that should be used
        for validation (e.g., int or list[int]).
        """
        if self.is_classifier():
            return as_classifier(self.result_type).get_type()
        return self.result_type

    def get_result_type_str(self) -> str:
        """Get a string representation of the result type."""
        if self.is_classifier():
            return (
                f"Provide the integer indices of your chosen labels: "
                f"{as_classifier(self.result_type).get_indexed_labels()}"
            )
        else:
            type_adapter = get_type_adapter(self.get_result_type())
            try:
                return json.dumps(type_adapter.json_schema())
            except Exception:
                return str(self.get_result_type())

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

        result_type = self.get_result_type()

        if result_type is None:
            if raw_result is None:
                return None
            else:
                raise ValueError("Result type is None but result is not None")
        elif raw_result is None:
            raise ValueError("Result is None but result type is not None")

        type_adapter = get_type_adapter(result_type)
        return type_adapter.validate_python(raw_result)

    def get_prompt(self) -> str:
        """Get the rendered prompt for this task.

        Uses the task's prompt_template (or default if None) and renders it with
        this task instance as the `task` variable.
        """
        prompt = Template(source=self.prompt_template).render(task=self)

        return prompt

    async def run_async(
        self,
        *,
        thread: Thread | str | None = None,
        raise_on_failure: bool = True,
        handlers: list["Handler | AsyncHandler"] = None,
    ) -> T:
        import marvin.engine.orchestrator

        orchestrator = marvin.engine.orchestrator.Orchestrator(
            tasks=[self],
            thread=thread,
            handlers=handlers,
        )
        await orchestrator.run(raise_on_failure=raise_on_failure)
        return self.result

    def run(
        self,
        *,
        thread: Thread | str | None = None,
        raise_on_failure: bool = True,
    ) -> T:
        return run_sync(
            self.run_async(thread=thread, raise_on_failure=raise_on_failure),
        )

    def get_end_turn_tools(self) -> list[type["marvin.engine.end_turn.EndTurn"]]:
        """Get the result tool for this task."""
        import marvin.engine.end_turn

        tools = []
        tools.append(marvin.engine.end_turn.MarkTaskSuccessful.prepare_for_task(self))
        if self.allow_fail:
            tools.append(marvin.engine.end_turn.MarkTaskFailed.prepare_for_task(self))
        if self.allow_skip:
            tools.append(marvin.engine.end_turn.MarkTaskSkipped.prepare_for_task(self))

        return tools

    # ------ State Management ------

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

    def mark_skipped(self) -> None:
        """Mark the task as skipped."""
        self.state = TaskState.SKIPPED

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

    def is_skipped(self) -> bool:
        """Check if the task is skipped."""
        return self.state == TaskState.SKIPPED

    def is_incomplete(self) -> bool:
        """Check if the task is incomplete."""
        return self.state in (TaskState.PENDING, TaskState.RUNNING)

    def is_complete(self) -> bool:
        """Check if the task is complete."""
        return self.state in (TaskState.SUCCESSFUL, TaskState.FAILED, TaskState.SKIPPED)

    def is_ready(self) -> bool:
        """Check if the task is ready to run.

        A task is ready if it is incomplete and all of its dependencies (including subtasks) are complete.
        """
        return self.is_incomplete() and all(
            t.is_complete() for t in (self.depends_on | self.subtasks)
        )

    def __enter__(self):
        """Set this task as the current task in context."""
        token = _current_task.set(self)
        self._tokens.append(token)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        """Reset the current task in context."""
        if self._tokens:  # Only reset if we have tokens
            _current_task.reset(self._tokens.pop())
