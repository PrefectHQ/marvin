from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from pydantic_ai.result import RunResult

import marvin
import marvin.agents.team
import marvin.engine.llm
from marvin.engine.end_turn import EndTurn
from marvin.engine.events import (
    AgentEndTurnEvent,
    AgentStartTurnEvent,
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
from marvin.utilities.logging import get_logger

T = TypeVar("T")

logger = get_logger(__name__)


@dataclass(kw_only=True)
class OrchestratorPrompt(Template):
    source: str | Path = Path("orchestrator.jinja")

    orchestrator: "Orchestrator"
    tasks: list[Task[Any]]
    instructions: list[str]
    end_turn_tools: list[EndTurn]


@dataclass(kw_only=True)
class Orchestrator:
    tasks: list[Task[Any]]
    thread: Thread
    handlers: list[Handler | AsyncHandler] = None
    active_team: marvin.agents.team.Team | None = field(init=False)

    def __post_init__(self):
        self.thread = get_thread(self.thread)
        if self.handlers is None:
            if marvin.settings.enable_default_print_handler:
                self.handlers = [PrintHandler()]
            else:
                self.handlers = []

    async def handle_event(self, event: Event):
        for handler in self.handlers:
            if isinstance(handler, AsyncHandler):
                await handler.handle(event)
            else:
                handler.handle(event)

    async def _run_turn(self, task: Task[T]):
        if task.is_pending():
            task.mark_running()
            if task.report_state_change:
                await self.thread.add_user_message_async(f"Task started: {task}")

        self.active_team = task.get_agent().as_team()

        self.active_team.start_turn()
        await self.handle_event(AgentStartTurnEvent(agent=self.active_team))

        # create end turn tools
        end_turn_tools = []
        for t in self.incomplete_tasks():
            end_turn_tools.extend(t.get_end_turn_tools())
        end_turn_tools.extend(self.active_team.get_end_turn_tools())

        orchestrator_prompt = OrchestratorPrompt(
            orchestrator=self,
            tasks=self.incomplete_tasks(),
            instructions=get_instructions(),
            end_turn_tools=end_turn_tools,
        )
        messages = await self.thread.get_messages_async()
        all_messages = [
            marvin.engine.llm.SystemMessage(content=orchestrator_prompt.render())
        ] + messages

        agentlet = self.active_team.get_agentlet(
            tools=task.get_tools(),
            result_types=end_turn_tools,
            result_tool_name="end_turn",
            result_tool_description="This tool will end your turn.",
        )

        result = await agentlet.run("", message_history=all_messages)

        await self._record_messages(result)

        # if task.report_state_change:
        #     if result:
        #         await self.thread.add_user_message_async(f'Task "{task.id}" completed.')
        #     else:
        #         await self.thread.add_user_message_async(f'Task "{task.id}" failed.')

        self.active_team.end_turn()
        end_turn = result.data
        await end_turn.run(orchestrator=self)
        await self.handle_event(AgentEndTurnEvent(agent=self.active_team))

        return result

    async def _record_messages(self, result):
        agent = self.active_team
        if isinstance(self.active_team, marvin.agents.team.Team):
            agent = self.active_team.active_agent

        for message in result.new_messages():
            for event in message_to_events(agent=agent, message=message):
                await self.handle_event(event)
        await self.thread.add_messages_async(result.new_messages())

    def incomplete_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.is_incomplete()]

    async def run(self, raise_on_failure: bool = True) -> list[RunResult]:
        results = []
        with self.thread:
            await self.handle_event(OrchestratorStartEvent())

            try:
                while incomplete_tasks := self.incomplete_tasks():
                    task = incomplete_tasks[0]
                    result = await self._run_turn(task)
                    results.append(result)

                    if raise_on_failure:
                        if failed := next(
                            (t for t in incomplete_tasks if t.is_failed()), False
                        ):
                            raise ValueError(f"Task {failed.id} failed")

                await self.handle_event(OrchestratorEndEvent())

            except Exception as e:
                await self.handle_event(OrchestratorExceptionEvent(error=str(e)))
                raise
