from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar
from uuid import UUID

if TYPE_CHECKING:
    pass
TaskResult = TypeVar("TaskResult")


@dataclass(kw_only=True)
class EndTurn:
    def run(self) -> None:
        pass


@dataclass(kw_only=True)
class MarkTaskSuccess(EndTurn, Generic[TaskResult]):
    """
    Mark a task successful and provide a result.
    """

    task_id: UUID
    result: TaskResult


@dataclass
@dataclass(kw_only=True)
class DelegateToAgent(EndTurn):
    """
    Delegate your turn to another agent.
    """

    agent_id: UUID


# @dataclass(kw_only=True)
# class TaskSuccess(EndTurn, Generic[TaskResult]):
#     """
#     Mark a task successful and provide a result.
#     """

#     task_id: UUID
#     task: SkipJsonSchema[Task[TaskResult]]
#     result: TaskResult

#     @classmethod
#     def prepare_for_task(cls, task: Task[TaskResult]) -> type["TaskSuccess"]:
#         task_ = task

#         @dataclass(kw_only=True)
#         class TaskSuccess(cls, Generic[TaskResult]):
#             task_id: UUID = field(default=task_.id, init=False)
#             task: SkipJsonSchema[Task[TaskResult]] = field(
#                 default_factory=lambda: task_, init=False, repr=False
#             )

#         TaskSuccess.__name__ = f"Success-Task-{task_.id.hex[:8]}"
#         TaskSuccess.__doc__ = f"Mark task {task_.id} successful and provide a result."

#         return TaskSuccess[task_.get_result_type()]

#     def run(self) -> None:
#         self.task.mark_successful(self.result)


# @dataclass(kw_only=True)
# class TaskFail(EndTurn):
#     task_id: UUID
#     error_message: str
#     task: SkipJsonSchema[Task] = field(repr=False)

#     @classmethod
#     def prepare_for_task(cls, task: Task) -> type["TaskFail"]:
#         task_ = task

#         @dataclass(kw_only=True)
#         class TaskFail(cls):
#             task_id: UUID = field(default=task_.id, init=False)
#             task: SkipJsonSchema[Task] = field(default=task_, init=False, repr=False)

#         TaskFail.__name__ = f"Fail-Task-{task_.id.hex[:8]}"
#         TaskFail.__doc__ = f"Mark task {task_.id} failed."
#         return TaskFail

#     def run(self) -> None:
#         self.task.mark_failed(self.error_message)


# @dataclass(kw_only=True)
# class TaskSkip(EndTurn):
#     task_id: UUID
#     task: SkipJsonSchema[Task] = field(repr=False)

#     @classmethod
#     def prepare_for_task(cls, task: Task) -> type["TaskSkip"]:
#         task_ = task

#         @dataclass(kw_only=True)
#         class TaskSkip(cls):
#             task_id: UUID = field(default=task_.id, init=False)
#             task: SkipJsonSchema[Task] = field(default=task_, init=False, repr=False)

#         TaskSkip.__name__ = f"Skip-Task-{task_.id.hex[:8]}"
#         TaskSkip.__doc__ = f"Mark task {task_.id} skipped."

#         return TaskSkip

#     def run(self) -> None:
#         self.task.mark_skipped()


# @dataclass(kw_only=True)
# class AgentDelegate(EndTurn):
#     delegate_id: UUID = field(
#         metadata={"description": "ID of the agent to delegate to"}
#     )
#     delegate: SkipJsonSchema[Actor]
#     team: SkipJsonSchema[Team]

#     def run(self) -> None:
#         self.team.active_agent = self.delegate
#         get_current_thread().add_user_message(
#             f"Delegated to Agent {self.delegate.name} ({self.delegate.id})"
#         )

#     @classmethod
#     def prepare_for_team(cls, team: Team) -> list[type["AgentDelegate"]]:
#         team_ = team

#         agent_delegates = []

#         for delegate_ in team_.get_delegates():

#             @dataclass(kw_only=True)
#             class AgentDelegate(cls):
#                 """
#                 Delegate your turn to another agent.
#                 """

#                 delegate_id: UUID = field(default=delegate_.id, init=False)
#                 delegate: SkipJsonSchema[Actor] = field(
#                     default_factory=lambda: delegate_, init=False, repr=False
#                 )
#                 team: SkipJsonSchema[Team] = field(
#                     default_factory=lambda: team_, init=False, repr=False
#                 )

#             AgentDelegate.__name__ = f"Delegate-To-Agent-{delegate_.id.hex[:8]}"
#             AgentDelegate.__doc__ = f"End your turn by delegating to Agent {delegate_.name} with ID {delegate_.id}"

#             agent_delegates.append(AgentDelegate)

#         return agent_delegates
