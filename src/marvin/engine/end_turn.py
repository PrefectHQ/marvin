from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, TypeVar
from uuid import UUID

from marvin.engine.llm import AgentMessage
from marvin.utilities.logging import get_logger

if TYPE_CHECKING:
    from marvin.engine.orchestrator import Orchestrator
TaskResult = TypeVar("TaskResult")

logger = get_logger(__name__)


@dataclass(kw_only=True)
class EndTurn:
    async def run(self, orchestrator: "Orchestrator") -> None:
        pass


@dataclass(kw_only=True)
class TaskSuccess(EndTurn, Generic[TaskResult]):
    """
    Mark a task successful and provide a result.
    """

    task_id: UUID
    result: TaskResult

    async def run(self, orchestrator: "Orchestrator") -> None:
        tasks = {t.id: t for t in orchestrator.tasks}
        if self.task_id not in tasks:
            raise ValueError(f"Task ID {self.task_id} not found in tasks")

        debug_result = (
            f'"{self.result}"' if isinstance(self.result, str) else self.result
        )
        logger.debug(
            f"Marking {tasks[self.task_id].friendly_name()} successful with result {debug_result}"
        )
        tasks[self.task_id].mark_successful(self.result)


@dataclass(kw_only=True)
class TaskFailed(EndTurn):
    """
    Mark a task failed and provide a message.
    """

    task_id: UUID
    message: str | None = None

    async def run(self, orchestrator: "Orchestrator") -> None:
        tasks = {t.id: t for t in orchestrator.tasks}
        if self.task_id not in tasks:
            raise ValueError(f"Task ID {self.task_id} not found in tasks")
        logger.debug(
            f'Marking {tasks[self.task_id].friendly_name()} failed with message "{self.message}"'
        )
        tasks[self.task_id].mark_failed(self.message)


@dataclass(kw_only=True)
class TaskSkipped(EndTurn):
    """
    Mark a task skipped.
    """

    task_id: UUID

    async def run(self, orchestrator: "Orchestrator") -> None:
        tasks = {t.id: t for t in orchestrator.tasks}
        if self.task_id not in tasks:
            raise ValueError(f"Task ID {self.task_id} not found in tasks")
        logger.debug(f"Marking {tasks[self.task_id].friendly_name()} skipped")
        tasks[self.task_id].mark_skipped()


@dataclass(kw_only=True)
class PostMessage(EndTurn):
    """
    Post a message to the thread.
    """

    message: str

    async def run(self, orchestrator: "Orchestrator") -> None:
        logger.debug(f"Posting message to thread: {self.message}")
        await orchestrator.thread.add_message_async(AgentMessage(content=self.message))


@dataclass(kw_only=True)
class DelegateToAgent(EndTurn):
    """
    Delegate your turn to another agent.
    """

    agent_id: UUID
    message: str | None = field(
        default=None,
        metadata={"description": "An optional message to send to the delegate"},
    )

    async def run(self, orchestrator: "Orchestrator") -> None:
        delegates = {d.id: d for d in orchestrator.active_team.get_delegates()}
        if self.agent_id not in delegates:
            raise ValueError(f"Agent ID {self.agent_id} not found in delegates")
        logger.debug(
            f'Delegating to agent "{delegates[self.agent_id].name}" with message "{self.message}"'
        )
        orchestrator.active_team.active_agent = delegates[self.agent_id]
        if self.message:
            await orchestrator.thread.add_messages_async(
                [AgentMessage(content=self.message)]
            )
