import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, TypeVar

import marvin.agents.team
from marvin.engine.llm import AgentMessage
from marvin.utilities.logging import get_logger

if TYPE_CHECKING:
    from marvin.engine.orchestrator import Orchestrator
TaskResult = TypeVar("TaskResult")

logger = get_logger(__name__)


@dataclass(kw_only=True)
class EndTurn(abc.ABC):
    @abc.abstractmethod
    async def run(self, orchestrator: "Orchestrator") -> None:
        pass

    @staticmethod
    @abc.abstractmethod
    def instructions() -> str:
        """Put instructions here since they docstrings do not survive all transformations (e.g. typing a generic)"""
        return ""


@dataclass(kw_only=True)
class MarkTaskSuccessful(EndTurn, Generic[TaskResult]):
    """Mark a task successful and provide a result."""

    task_id: str
    result: TaskResult

    async def run(self, orchestrator: "Orchestrator") -> None:
        tasks = {t.id: t for t in orchestrator.tasks}
        if self.task_id not in tasks:
            raise ValueError(f"Task ID {self.task_id} not found in tasks")

        debug_result = (
            f'"{self.result}"' if isinstance(self.result, str) else self.result
        )
        logger.debug(
            f"{orchestrator.active_agent().friendly_name()}: Marking {tasks[self.task_id].friendly_name()} successful with result {debug_result}",
        )
        tasks[self.task_id].mark_successful(self.result)

    @staticmethod
    def instructions() -> str:
        return "Mark a task successful and provide a result."


@dataclass(kw_only=True)
class MarkTaskFailed(EndTurn):
    """Mark a task failed and provide a message."""

    task_id: str
    message: str | None = None

    async def run(self, orchestrator: "Orchestrator") -> None:
        tasks = {t.id: t for t in orchestrator.tasks}
        if self.task_id not in tasks:
            raise ValueError(f"Task ID {self.task_id} not found in tasks")
        logger.debug(
            f'{orchestrator.active_agent().friendly_name()}: Marking {tasks[self.task_id].friendly_name()} failed with message "{self.message}"',
        )
        tasks[self.task_id].mark_failed(self.message)

    @staticmethod
    def instructions() -> str:
        return "Mark a task failed and provide a message."


@dataclass(kw_only=True)
class MarkTaskSkipped(EndTurn):
    """Mark a task skipped."""

    task_id: str

    async def run(self, orchestrator: "Orchestrator") -> None:
        tasks = {t.id: t for t in orchestrator.tasks}
        if self.task_id not in tasks:
            raise ValueError(f"Task ID {self.task_id} not found in tasks")
        logger.debug(
            f"{orchestrator.active_agent().friendly_name()}: Marking {tasks[self.task_id].friendly_name()} skipped",
        )
        tasks[self.task_id].mark_skipped()

    @staticmethod
    def instructions() -> str:
        return "Mark a task skipped."


@dataclass(kw_only=True)
class PostMessage(EndTurn):
    """Post a message to the thread."""

    message: str

    async def run(self, orchestrator: "Orchestrator") -> None:
        logger.debug(
            f"{orchestrator.active_agent().friendly_name()}: Posting message to thread: {self.message}",
        )
        await orchestrator.thread.add_message_async(AgentMessage(content=self.message))

    @staticmethod
    def instructions() -> str:
        return "Post a message to the thread."


@dataclass(kw_only=True)
class DelegateToAgent(EndTurn):
    """Delegate your turn to another agent."""

    agent_id: str
    message: str | None = field(
        default=None,
        metadata={"description": "An optional message to send to the delegate"},
    )

    async def run(self, orchestrator: "Orchestrator") -> None:
        current_agent_name = orchestrator.active_agent().friendly_name()
        delegates = {d.id: d for d in orchestrator.get_delegates()}
        if self.agent_id not in delegates:
            raise ValueError(f"Agent ID {self.agent_id} not found in delegates")
        logger.debug(
            f'{current_agent_name}: Delegating to {delegates[self.agent_id].friendly_name()} with message "{self.message}"',
        )

        # walk active_agents to find the delegate
        current = orchestrator.team

        while self.agent_id not in {a.id for a in current.members}:
            if not isinstance(current, marvin.agents.team.Team):
                raise ValueError(f"Agent ID {self.agent_id} not found in delegates")
            current = current.active_member

        current.active_member = next(
            a for a in current.members if a.id == self.agent_id
        )

        if self.message:
            await orchestrator.thread.add_messages_async(
                [AgentMessage(content=f"{current_agent_name}: {self.message}")],
            )

    @staticmethod
    def instructions() -> str:
        return "Delegate your turn to another agent."
