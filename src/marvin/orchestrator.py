from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Optional, TypeVar, Union
from uuid import UUID
import marvin
import marvin.engine.llm
from marvin.agents.agent import Agent
from marvin.engine.thread import Thread, get_thread
from marvin.prompts import Template
from marvin.tasks.task import Task
import pydantic_ai

T = TypeVar("T")


class OrchestratorPrompt(Template):
    template_path: Path = Path("orchestrator.jinja")

    agent: Agent
    tasks: list[Task]
    instructions: list[str]


@dataclass
class EndTurn:
    end_turn: bool


@dataclass
class TaskResult(Generic[T]):
    """
    To mark a task successful, provide its ID and a result
    """

    task_id: UUID
    result: T


@dataclass
class Orchestrator:
    tasks: list[Task]
    thread: Thread
    prompt: str = None

    def __init__(self, tasks: list[Task], thread: Optional[str | Thread] = None):
        self.thread = get_thread(thread)
        self.tasks = tasks

    async def run(self, raise_on_failure: bool = True):
        # TODO: expand to include all children of provided tasks
        while incomplete_tasks := [t for t in self.tasks if t.is_incomplete()]:
            task = incomplete_tasks[0]

            if task.is_pending():
                task.mark_running()
                await self.thread.add_messages(
                    [marvin.engine.llm.UserMessage(content=f"New task started: {task}")]
                )

            agent = task.get_agent()

            system_prompt = OrchestratorPrompt(
                agent=agent,
                tasks=incomplete_tasks,
                instructions=[],
            )

            task_results = []
            for task in incomplete_tasks:
                task_results.append(TaskResult[task.result_type])

            agentlet = marvin.engine.llm.create_agentlet(
                model=agent.get_model(),
                result_type=Union[tuple(task_results)],
                system_prompt=system_prompt.render(),
                tools=agent.tools,
            )

            @agentlet.result_validator
            async def validate_result(
                ctx: pydantic_ai.RunContext, result: TaskResult
            ) -> TaskResult:
                task_id = result.task_id
                task = next((t for t in self.tasks if t.id == task_id), None)
                if not task:
                    raise pydantic_ai.ModelRetry(
                        f'Task ID "{task_id}" not found. Valid task IDs: {[t.id for t in self.tasks]}'
                    )

                try:
                    task.mark_successful(result.result)
                except Exception as e:
                    raise pydantic_ai.ModelRetry(f'Task "{task_id}" failed: {e}') from e
                return result

            messages = await self.thread.get_messages()
            result = await agentlet.run("", message_history=messages)

            await self.thread.add_messages(result.new_messages())

            if raise_on_failure and (
                failed := next((t for t in incomplete_tasks if t.is_failed()), False)
            ):
                raise ValueError(f"Task {failed.id} failed")
