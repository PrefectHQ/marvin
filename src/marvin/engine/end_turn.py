from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from marvin.engine.llm import AgentMessage
from marvin.utilities.logging import get_logger, maybe_quote

if TYPE_CHECKING:
    from marvin.agents.actor import Actor
    from marvin.agents.team import Team
    from marvin.engine.orchestrator import Orchestrator
    from marvin.tasks.task import Task

TaskResult = TypeVar("TaskResult")


logger = get_logger(__name__)


class EndTurn:
    async def run(self, orchestrator: "Orchestrator", actor: "Actor") -> None:
        pass


class MarkTask(EndTurn):
    task: ClassVar["Task[Any]"]


class MarkTaskSuccessful(MarkTask):
    pass


def create_mark_task_successful(mark_task: "Task[Any]") -> type[MarkTaskSuccessful]:
    @dataclass(kw_only=True)
    class _MarkTaskSuccessful(MarkTaskSuccessful, Generic[TaskResult]):
        """Mark a task successful and provide a result."""

        result: TaskResult
        task = mark_task

        def __post_init__(self):
            mark_task.validate_result(self.result)

        async def run(self, orchestrator: "Orchestrator", actor: "Actor") -> None:
            logger.debug(
                f"{actor.friendly_name()}: Marking {mark_task.friendly_name()} successful."
            )
            mark_task.mark_successful(self.result)
            await orchestrator.thread.add_user_message_async(
                f"Task completed: {mark_task.friendly_name()}"
            )

    _MarkTaskSuccessful.__name__ = f"MarkTaskSuccessful_{mark_task.id}"
    return _MarkTaskSuccessful[mark_task.get_result_type()]


class MarkTaskFailed(MarkTask):
    pass


def create_mark_task_failed(mark_task: "Task[Any]") -> type[MarkTaskFailed]:
    @dataclass(kw_only=True)
    class _MarkTaskFailed(MarkTaskFailed):
        """Mark a task failed and provide a message."""

        message: str | None = None
        task = mark_task

        async def run(self, orchestrator: "Orchestrator", actor: "Actor") -> None:
            if self.message:
                logger.debug(
                    f"{actor.friendly_name()}: Marking {mark_task.friendly_name()} failed with message {maybe_quote(self.message)}",
                )
            else:
                logger.debug(
                    f"{actor.friendly_name()}: Marking {mark_task.friendly_name()} failed",
                )
            mark_task.mark_failed(self.message)
            await orchestrator.thread.add_user_message_async(
                f"Task failed: {mark_task.friendly_name()}"
            )

    _MarkTaskFailed.__name__ = f"MarkTaskFailed_{mark_task.id}"
    return _MarkTaskFailed


class MarkTaskSkipped(MarkTask):
    pass


def create_mark_task_skipped(mark_task: "Task[Any]") -> type[MarkTaskSkipped]:
    @dataclass(kw_only=True)
    class _MarkTaskSkipped(MarkTaskSkipped):
        """Mark a task skipped."""

        task = mark_task

        async def run(self, orchestrator: "Orchestrator", actor: "Actor") -> None:
            logger.debug(
                f"{actor.friendly_name()}: Marking {mark_task.friendly_name()} skipped",
            )
            mark_task.mark_skipped()
            await orchestrator.thread.add_user_message_async(
                f"Task skipped: {mark_task.friendly_name()}"
            )

    _MarkTaskSkipped.__name__ = f"MarkTaskSkipped_{mark_task.id}"
    return _MarkTaskSkipped


@dataclass(kw_only=True)
class PostMessage(EndTurn):
    """Post a message to the thread."""

    message: str

    async def run(self, orchestrator: "Orchestrator", actor: "Actor") -> None:
        logger.debug(
            f"{actor.friendly_name()}: Posting message to thread: {self.message}",
        )
        await orchestrator.thread.add_message_async(AgentMessage(content=self.message))


class DelegateToActor(EndTurn):
    actor: ClassVar["Actor"]


def create_delegate_to_actor(
    delegate_actor: "Actor", team: "Team | None" = None
) -> type[DelegateToActor]:
    @dataclass(kw_only=True)
    class _DelegateToActor(DelegateToActor):
        message: str | None = field(
            default=None,
            metadata={"description": "An optional message to send to the delegate"},
        )
        actor = delegate_actor

        async def run(self, orchestrator: "Orchestrator", actor: "Actor"):
            if team is not None:
                team.active_member = delegate_actor

            if self.message:
                await orchestrator.thread.add_messages_async(
                    [AgentMessage(content=f"{actor.friendly_name()}: {self.message}")],
                )

    _DelegateToActor.__name__ = f"delegate_to_actor_{delegate_actor.id}"
    return _DelegateToActor
