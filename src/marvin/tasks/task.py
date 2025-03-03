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
    Annotated,
    Any,
    Generic,
    Literal,
    Optional,
    Sequence,
    TypeAlias,
    TypeVar,
)

from pydantic import TypeAdapter
from pydantic_ai.messages import UserContent

import marvin
import marvin.thread
from marvin.agents.actor import Actor
from marvin.agents.team import Swarm, Team
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.thread import Thread
from marvin.utilities.asyncio import run_sync
from marvin.utilities.types import Labels, as_classifier, is_classifier

if TYPE_CHECKING:
    from marvin.engine.end_turn import EndTurn
    from marvin.engine.handlers import AsyncHandler, Handler

T = TypeVar("T")
NOTSET: Literal["__NOTSET__"] = "__NOTSET__"

# Global context var for current task
_current_task: ContextVar[Optional["Task[Any]"]] = ContextVar(
    "current_task",
    default=None,
)

_type_adapters: dict[type[Any], TypeAdapter[Any]] = {}


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


ResultType: TypeAlias = type[T] | Annotated[Any, Any] | Labels | Literal["__NOTSET__"]


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

    attachments: Sequence[UserContent] = field(
        default_factory=list,
        metadata={"description": "Attachments to the task"},
    )

    result_type: ResultType[T] = field(  # type: ignore[reportRedeclaration]
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

    actor: Actor | None = field(
        default=None,
        metadata={
            "description": "The actor assigned to this task. If not provided, the default agent will be used.",
        },
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

    verbose: bool = field(
        default=False,
        metadata={
            "description": "Verbose tasks print additional information to the thread, such as the fact that they started or completed.",
        },
    )

    _parent: "Task[Any] | None" = field(
        default=None,
        metadata={"description": "Optional parent task"},
        init=False,
        repr=False,
    )

    subtasks: set["Task[Any]"] = field(
        default_factory=set,
        metadata={
            "description": "List of subtasks, or tasks for which this task is the parent"
        },
        init=False,
        repr=False,
    )

    depends_on: set["Task[Any]"] = field(
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
        instructions: str | Sequence[UserContent],
        attachments: Sequence[UserContent] | None = None,
        result_type: ResultType[T] = NOTSET,
        *,
        name: str | None = None,
        prompt_template: str | Path = Path("task.jinja"),
        agents: list[Actor | Team] | None = None,
        context: dict[str, Any] | None = None,
        tools: list[Callable[..., Any]] | None = None,
        memories: list[Memory] | None = None,
        result_validator: Callable[..., Any] | None = None,
        parent: "Task[Any] | None | Literal['__NOTSET__']" = NOTSET,
        depends_on: Sequence["Task[Any]"] | None = None,
        allow_fail: bool = False,
        allow_skip: bool = False,
        verbose: bool = False,
        cli: bool = False,
        plan: bool = False,
    ) -> None:
        """Initialize a Task.

        Args:
            instructions: Instructions for the task
            attachments: Optional attachments to the task
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
            verbose: Whether to print additional status messages to the active thread
            cli: Whether to enable CLI interaction tools
            plan: Whether to enable a tool for planning subtasks

        """
        # required fields
        if isinstance(instructions, str):
            self.instructions = instructions
        else:
            self.instructions = "\n\n".join(
                [i for i in instructions if isinstance(i, str)]
            )
            attachments = (attachments or []) + [
                i for i in instructions if not isinstance(i, str)
            ]

        # optional fields with defaults
        self.attachments = attachments or []
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
        self.plan = plan
        self.verbose = verbose
        # key fields
        self.id = uuid.uuid4().hex[:8]
        self.state = TaskState.PENDING
        self.result = None

        # if no parent is provided, use the current task from context
        if parent is NOTSET:
            parent = _current_task.get()
        self.parent = parent
        self.subtasks: set[Task[Any]] = set()
        self.depends_on: set[Task[Any]] = set(depends_on or [])

        # internal fields
        self._tokens = []

        if agents:
            if len(agents) == 1:
                self.actor = agents[0]
            else:
                self.actor = Swarm(members=agents)

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
            if any(isinstance(x, (list, tuple, set)) for x in self.result_type):
                raise ValueError(
                    "Invalid nested list format - use [['a', 'b']] for multi-label",
                )
            self.result_type = Labels(self.result_type)

    def friendly_name(self, verbose: bool = True) -> str:
        """Get a friendly name for this task."""
        if self.name:
            return f'Task {self.id} ("{self.name}")'
        if verbose:
            # Replace consecutive newlines with a single space
            instructions = " ".join(self.instructions.split())
            return f'Task {self.id} ("{instructions[:40]}...")'
        else:
            return f"Task {self.id}"

    @property
    def parent(self) -> "Task[Any] | None":
        """Get the parent task of this task."""
        return self._parent

    @parent.setter
    def parent(self, value: "Task[Any] | None") -> None:
        """Set the parent task of this task."""
        if self._parent is not None:
            self._parent.subtasks.discard(self)
        self._parent = value
        if self._parent is not None:
            self._parent.subtasks.add(self)

    def get_actor(self) -> Actor:
        """Retrieve the actor assigned to this task."""
        return self.actor or marvin.defaults.agent

    def get_tools(self) -> list[Callable[..., Any]]:
        """Get the tools assigned to this task."""
        tools: list[Callable[..., Any]] = []
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

    def get_prompt(self) -> str | Sequence[UserContent]:
        """Get the rendered prompt for this task.

        Uses the task's prompt_template (or default if None) and renders it with
        this task instance as the `task` variable.
        """
        return [
            Template(source=self.prompt_template).render(task=self),
            *self.attachments,
        ]

    async def run_async(
        self,
        *,
        thread: Thread | str | None = None,
        raise_on_failure: bool = True,
        handlers: list["Handler | AsyncHandler"] | None = None,
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

    def get_end_turn_tools(self) -> list[type["EndTurn"]]:
        """Get the result tool for this task."""
        import marvin.engine.end_turn

        tools: list[type[marvin.engine.end_turn.EndTurn]] = []
        tools.append(self.mark_successful_tool())
        if self.allow_fail:
            tools.append(self.mark_failed_tool())
        if self.allow_skip:
            tools.append(self.mark_skipped_tool())
        if self.plan:
            tools.append(marvin.engine.end_turn.create_plan_subtasks(parent_task=self))

        return tools

    def mark_successful_tool(self) -> type["marvin.engine.end_turn.MarkTaskSuccessful"]:
        import marvin.engine.end_turn

        return marvin.engine.end_turn.create_mark_task_successful(self)

    def mark_failed_tool(self) -> type["marvin.engine.end_turn.MarkTaskFailed"]:
        import marvin.engine.end_turn

        return marvin.engine.end_turn.create_mark_task_failed(self)

    def mark_skipped_tool(self) -> type["marvin.engine.end_turn.MarkTaskSkipped"]:
        import marvin.engine.end_turn

        return marvin.engine.end_turn.create_mark_task_skipped(self)

    # ------ State Management ------

    async def mark_successful(
        self,
        result: T = None,
        validate_result: bool = True,
        thread: Thread | None = None,
    ) -> None:
        """Mark the task as successful with an optional result."""
        if validate_result:
            result = self.validate_result(result)
        self.result = result
        self.state = TaskState.SUCCESSFUL
        if thread is None:
            thread = marvin.thread.get_current_thread()

        if thread and self.verbose:
            await thread.add_info_message_async(
                f"{self.friendly_name()} successful with result {result}",
                prefix="Task state updated",
            )

    async def mark_failed(self, error: str, thread: Thread | None = None) -> None:
        """Mark the task as failed with an error message."""
        self.result = error
        self.state = TaskState.FAILED
        if thread is None:
            thread = marvin.thread.get_current_thread()

        if thread and self.verbose:
            await thread.add_info_message_async(
                f"{self.friendly_name()} failed with error {error}",
                prefix="Task state updated",
            )

    async def mark_running(
        self,
        thread: Thread | None = None,
    ) -> None:
        """Mark the task as running."""
        self.state = TaskState.RUNNING

        if thread is None:
            thread = marvin.thread.get_current_thread()

        if thread:
            await thread.add_user_message_async(
                self.get_prompt(),
            )

    async def mark_skipped(self, thread: Thread | None = None) -> None:
        """Mark the task as skipped."""
        self.state = TaskState.SKIPPED
        if thread is None:
            thread = marvin.thread.get_current_thread()

        if thread and self.verbose:
            await thread.add_info_message_async(
                f"{self.friendly_name()} skipped",
                prefix="Task state updated",
            )

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
