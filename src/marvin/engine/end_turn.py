import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar

from pydantic_ai import ModelRetry

from marvin.engine.llm import AgentMessage
from marvin.utilities.logging import get_logger

if TYPE_CHECKING:
    from marvin.engine.orchestrator import Orchestrator
    from marvin.tasks.task import Task
TaskResult = TypeVar("TaskResult")

logger = get_logger(__name__)


@dataclass(kw_only=True)
class EndTurn(abc.ABC):
    @abc.abstractmethod
    async def run(self, orchestrator: "Orchestrator") -> None:
        pass


@dataclass(kw_only=True)
class TaskStateEndTurn(EndTurn):
    task_id: str


@dataclass(kw_only=True)
class MarkTaskSuccessful(TaskStateEndTurn, Generic[TaskResult]):
    """Mark a task successful and provide a result."""

    task_id: str
    result: TaskResult

    async def run(self, orchestrator: "Orchestrator") -> None:
        tasks: dict[str, "Task[Any]"] = {t.id: t for t in orchestrator.get_all_tasks()}
        if self.task_id not in tasks:
            raise ModelRetry(f"Task ID {self.task_id} not found in tasks")

        task = tasks[self.task_id]
        agent_name = orchestrator.active_agent().friendly_name()
        result = repr(self.result) if isinstance(self.result, str) else self.result
        logger.debug(
            f"{agent_name}: Marking {task.friendly_name()} successful with result {result}",
        )
        task.mark_successful(self.result)

    @classmethod
    def prepare_for_task(cls, task: "Task[Any]") -> type[Any]:
        """
        We could let the LLM fill out the task_id itself, but Pydantic AI doesn't support multiple calls
        to final tools with the same name, which prevents parallel end turn calls.

        Therefore, we create custom classes for each task, which are named after the task ID.
        """

        @dataclass(kw_only=True, init=False)
        class MarkTaskSuccessful(cls, Generic[TaskResult]):
            task_id: Literal[task.id] = field(default=task.id, init=False)  # noqa

        MarkTaskSuccessful.__name__ = f"MarkTaskSuccessful_{task.id}"
        return MarkTaskSuccessful[task.get_result_type()]


@dataclass(kw_only=True)
class MarkTaskFailed(TaskStateEndTurn):
    """Mark a task failed and provide a message."""

    task_id: str
    message: str | None = None

    async def run(self, orchestrator: "Orchestrator") -> None:
        tasks = {t.id: t for t in orchestrator.get_all_tasks()}
        if self.task_id not in tasks:
            raise ModelRetry(f"Task ID {self.task_id} not found in tasks")

        task = tasks[self.task_id]
        agent_name = orchestrator.active_agent().friendly_name()
        if self.message:
            logger.debug(
                f"{agent_name}: Marking {task.friendly_name()} failed with message {repr(self.message)}",
            )
        else:
            logger.debug(
                f"{agent_name}: Marking {task.friendly_name()} failed",
            )
        task.mark_failed(self.message)

    @classmethod
    def prepare_for_task(cls, task: "Task[Any]") -> None:
        """
        Create a custom class for this task to support parallel end turn calls.
        """

        @dataclass(kw_only=True)
        class MarkTaskFailed(cls):
            task_id: Literal[task.id] = field(default=task.id, init=False)  # noqa

        MarkTaskFailed.__name__ = f"MarkTaskFailed_{task.id}"
        return MarkTaskFailed


@dataclass(kw_only=True)
class MarkTaskSkipped(TaskStateEndTurn):
    """Mark a task skipped."""

    task_id: str

    async def run(self, orchestrator: "Orchestrator") -> None:
        tasks = {t.id: t for t in orchestrator.get_all_tasks()}
        if self.task_id not in tasks:
            raise ModelRetry(f"Task ID {self.task_id} not found in tasks")

        task = tasks[self.task_id]
        logger.debug(
            f"{orchestrator.active_agent().friendly_name()}: Marking {task.friendly_name()} skipped",
        )
        task.mark_skipped()

    @classmethod
    def prepare_for_task(cls, task: "Task[Any]") -> None:
        """
        Create a custom class for this task to support parallel end turn calls.
        """

        @dataclass(kw_only=True)
        class MarkTaskSkipped(cls):
            task_id: Literal[task.id] = field(default=task.id, init=False)  # noqa

        MarkTaskSkipped.__name__ = f"MarkTaskSkipped_{task.id}"
        return MarkTaskSkipped


@dataclass(kw_only=True)
class PostMessage(EndTurn):
    """Post a message to the thread."""

    message: str

    async def run(self, orchestrator: "Orchestrator") -> None:
        logger.debug(
            f"{orchestrator.active_agent().friendly_name()}: Posting message to thread: {self.message}",
        )
        await orchestrator.thread.add_message_async(AgentMessage(content=self.message))


@dataclass(kw_only=True)
class DelegateToAgent(EndTurn):
    """Delegate your turn to another agent."""

    agent_id: str
    message: str | None = field(
        default=None,
        metadata={"description": "An optional message to send to the delegate"},
    )

    async def run(self, orchestrator: "Orchestrator") -> None:
        orchestrator.stage_delegate(self.agent_id)

        # TODO: this may be redundant because the message can be seen in the tool call
        # if self.message:
        #     await orchestrator.thread.add_messages_async(
        #         [AgentMessage(content=f"{current_agent_name}: {self.message}")],
        #     )
