import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from marvin.engine.llm import AgentMessage
from marvin.utilities.logging import get_logger, maybe_quote

if TYPE_CHECKING:
    from marvin.agents.agent import Agent
    from marvin.engine.orchestrator import Orchestrator
    from marvin.tasks.task import Task
TaskResult = TypeVar("TaskResult")


logger = get_logger(__name__)


@dataclass(kw_only=True)
class EndTurn(abc.ABC):
    @abc.abstractmethod
    async def run(self, orchestrator: "Orchestrator", agent: "Agent") -> None:
        pass


class MarkTask(EndTurn):
    def get_task(self) -> "Task[Any]":
        raise NotImplementedError()


class MarkTaskSuccessful(MarkTask):
    pass


def create_mark_task_successful(task: "Task[Any]") -> MarkTaskSuccessful:
    @dataclass(kw_only=True)
    class _MarkTaskSuccessful(MarkTaskSuccessful, Generic[TaskResult]):
        """Mark a task successful and provide a result."""

        result: TaskResult

        async def run(self, orchestrator: "Orchestrator", agent: "Agent") -> None:
            logger.debug(
                f"{agent.friendly_name()}: Marking {task.friendly_name()} successful with result {maybe_quote(self.result)}"
            )
            task.mark_successful(self.result)

        def get_task(self) -> "Task[Any]":
            return task

    _MarkTaskSuccessful.__name__ = f"mark_task_{task.id}_successful"
    return _MarkTaskSuccessful[task.get_result_type()]


class MarkTaskFailed(MarkTask):
    pass


def create_mark_task_failed(task: "Task[Any]") -> type[MarkTaskFailed]:
    @dataclass(kw_only=True)
    class _MarkTaskFailed(MarkTaskFailed):
        """Mark a task failed and provide a message."""

        message: str | None = None

        async def run(self, orchestrator: "Orchestrator", agent: "Agent") -> None:
            if self.message:
                logger.debug(
                    f"{agent.friendly_name()}: Marking {task.friendly_name()} failed with message {maybe_quote(self.message)}",
                )
            else:
                logger.debug(
                    f"{agent.friendly_name()}: Marking {task.friendly_name()} failed",
                )
            task.mark_failed(self.message)

        def get_task(self) -> "Task[Any]":
            return task

    _MarkTaskFailed.__name__ = f"mark_task_{task.id}_failed"
    return _MarkTaskFailed


class MarkTaskSkipped(MarkTask):
    pass


def create_mark_task_skipped(task: "Task[Any]") -> type[MarkTaskSkipped]:
    @dataclass(kw_only=True)
    class _MarkTaskSkipped(MarkTaskSkipped):
        """Mark a task skipped."""

        async def run(self, orchestrator: "Orchestrator", agent: "Agent") -> None:
            logger.debug(
                f"{agent.friendly_name()}: Marking {task.friendly_name()} skipped",
            )
            task.mark_skipped()

        def get_task(self) -> "Task[Any]":
            return task

    _MarkTaskSkipped.__name__ = f"mark_task_{task.id}_skipped"
    return _MarkTaskSkipped


@dataclass(kw_only=True)
class PostMessage(EndTurn):
    """Post a message to the thread."""

    message: str

    async def run(self, orchestrator: "Orchestrator", agent: "Agent") -> None:
        logger.debug(
            f"{agent.friendly_name()}: Posting message to thread: {self.message}",
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
