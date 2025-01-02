from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, TypeVar
from uuid import UUID

import pydantic_ai

import marvin
import marvin.engine.llm
from marvin.agents.agent import Agent
from marvin.engine.events import (
    Event,
    OrchestratorEndEvent,
    OrchestratorExceptionEvent,
    OrchestratorStartEvent,
    message_to_events,
)
from marvin.engine.handlers import AsyncHandler, Handler
from marvin.engine.print_handler import PrintHandler
from marvin.engine.thread import Thread, get_thread
from marvin.instructions import get_instructions
from marvin.prompts import Template
from marvin.tasks.task import Task

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
    To mark a task successful, provide its ID and a result.
    """

    task_id: UUID
    result: T


@dataclass(kw_only=True)
class Orchestrator:
    tasks: list[Task]
    thread: Thread
    handlers: list[Handler | AsyncHandler] = field(default_factory=list)

    def __post_init__(self):
        self.thread = get_thread(self.thread)
        if marvin.settings.enable_default_print_handler and not self.handlers:
            self.handlers = [PrintHandler()]

    async def handle_event(self, event: Event):
        for handler in self.handlers:
            if isinstance(handler, AsyncHandler):
                await handler.handle(event)
            else:
                handler.handle(event)

    def _create_system_prompt(
        self, incomplete_tasks: list[Task]
    ) -> "marvin.engine.llm.ModelRequest":
        agent = incomplete_tasks[0].get_agent()
        system_prompt = OrchestratorPrompt(
            agent=agent,
            tasks=incomplete_tasks,
            instructions=get_instructions(),
        )
        return marvin.engine.llm.SystemMessage(content=system_prompt.render())

    def _create_result_validator(self):
        async def validate_result(
            ctx: pydantic_ai.RunContext,
            result: TaskResult,
        ) -> TaskResult:
            task_id = result.task_id
            task = next((t for t in self.tasks if t.id == task_id), None)
            if not task:
                raise pydantic_ai.ModelRetry(
                    f'Task ID "{task_id}" not found. Valid task IDs: {[t.id for t in self.tasks]}'
                )

            try:
                task.mark_successful(result.result)
            except ValueError as e:
                raise pydantic_ai.ModelRetry(f'Task "{task_id}" failed: {e}') from e
            return result

        return validate_result

    async def _execute_task(self, task: Task, incomplete_tasks: list[Task]):
        if task.is_pending():
            task.mark_running()
            if task.report_state_change:
                await self.thread.add_user_message_async(f"Task started: {task}")

        agent = task.get_agent()
        system_message = self._create_system_prompt(incomplete_tasks)

        # Create task results with appropriate result types
        task_results = [TaskResult[t.get_result_type()] for t in incomplete_tasks]
        agentlet = agent.get_agentlet(tools=task.get_tools(), result_types=task_results)
        agentlet.result_validator(self._create_result_validator())

        messages = await self.thread.get_messages_async()
        all_messages = [system_message] + messages

        result = await agentlet.run("", message_history=all_messages)

        if task.report_state_change:
            if result:
                await self.thread.add_user_message_async(
                    f'Task "{task.id}" completed: {result}'
                )
            else:
                await self.thread.add_user_message_async(f'Task "{task.id}" failed.')

        if result and hasattr(result, "new_messages"):
            await self.thread.add_messages_async(result.new_messages())

        return result

    async def _handle_agent_messages(self, agent: Agent, result):
        for message in result.new_messages():
            for event in message_to_events(agent=agent, message=message):
                await self.handle_event(event)
        await self.thread.add_messages_async(result.new_messages())

    async def run(self, raise_on_failure: bool = True):
        await self.handle_event(OrchestratorStartEvent())

        try:
            while incomplete_tasks := [t for t in self.tasks if t.is_incomplete()]:
                task = incomplete_tasks[0]
                result = await self._execute_task(task, incomplete_tasks)
                await self._handle_agent_messages(task.get_agent(), result)

                if raise_on_failure:
                    if failed := next(
                        (t for t in incomplete_tasks if t.is_failed()), False
                    ):
                        raise ValueError(f"Task {failed.id} failed")

            await self.handle_event(OrchestratorEndEvent())

        except Exception as e:
            await self.handle_event(OrchestratorExceptionEvent(error=str(e)))
            raise
