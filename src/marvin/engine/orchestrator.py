from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

import marvin
import marvin.agents.team
import marvin.engine.llm
from marvin.agents.actor import Actor
from marvin.agents.agent import Agent
from marvin.engine.end_turn_tools import DelegateToAgent, EndTurn, MarkTaskSuccess
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
    handlers: list[Handler | AsyncHandler] = field(default_factory=list)
    tasks_by_id: dict[UUID, Task[Any]] = field(init=False)
    agent: Actor | None = field(init=False)

    def __post_init__(self):
        self.thread = get_thread(self.thread)
        if marvin.settings.enable_default_print_handler and not self.handlers:
            self.handlers = [PrintHandler()]
        self.tasks_by_id = {t.id: t for t in self.tasks}

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

        self.agent = task.get_agent()

        if isinstance(self.agent, Agent) and self.agent.get_delegates():
            logger.warning(
                f"Agent {self.agent.id} has delegates, but is not part of a team. Delegates will not be used."
            )

        self.agent.start_turn()
        await self.handle_event(AgentStartTurnEvent(agent=self.agent))

        # create end turn tools
        end_turn_tools = []
        for t in self.incomplete_tasks():
            end_turn_tools.extend(t.get_end_turn_tools())
        end_turn_tools.extend(self.agent.get_end_turn_tools())

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

        agentlet = self.agent.get_agentlet(
            tools=task.get_tools(),
            result_types=end_turn_tools,
            result_tool_name="end_turn",
            result_tool_description="This tool will end your turn.",
            deps_type=OrchestrationContext,
        )
        result = await agentlet.run("", message_history=all_messages)

        self.handle_end_turn(end_turn=result.data)

        # if task.report_state_change:
        #     if result:
        #         await self.thread.add_user_message_async(f'Task "{task.id}" completed.')
        #     else:
        #         await self.thread.add_user_message_async(f'Task "{task.id}" failed.')

        if result:
            await self.thread.add_messages_async(result.new_messages())

        await self.handle_event(AgentEndTurnEvent(agent=self.agent))

        return result

    async def _handle_agent_messages(self, result):
        agent = self.agent
        if isinstance(self.agent, marvin.agents.team.Team):
            agent = self.agent.active_agent
        for message in result.new_messages():
            for event in message_to_events(agent=agent, message=message):
                await self.handle_event(event)
        await self.thread.add_messages_async(result.new_messages())

    def incomplete_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.is_incomplete()]

    async def run(self, raise_on_failure: bool = True):
        with self.thread:
            await self.handle_event(OrchestratorStartEvent())

            try:
                while incomplete_tasks := self.incomplete_tasks():
                    task = incomplete_tasks[0]
                    result = await self._run_turn(task)

                    await self._handle_agent_messages(result)

                    if raise_on_failure:
                        if failed := next(
                            (t for t in incomplete_tasks if t.is_failed()), False
                        ):
                            raise ValueError(f"Task {failed.id} failed")

                await self.handle_event(OrchestratorEndEvent())

            except Exception as e:
                await self.handle_event(OrchestratorExceptionEvent(error=str(e)))
                raise

    def handle_end_turn(self, end_turn: EndTurn):
        self.agent.end_turn()

        if isinstance(end_turn, MarkTaskSuccess):
            if end_turn.task_id not in self.tasks_by_id:
                raise ValueError(f"Task ID {end_turn.task_id} not found in tasks")
            self.tasks_by_id[end_turn.task_id].mark_successful(end_turn.result)

        elif isinstance(end_turn, DelegateToAgent):
            if not isinstance(self.agent, marvin.agents.team.Team):
                raise ValueError(
                    "Agent attempted to delegate to another agent, but is not part of a team"
                )
            delegates = {d.id: d for d in self.agent.get_delegates()}
            if end_turn.agent_id in delegates:
                self.agent.active_agent = delegates[end_turn.agent_id]
            else:
                raise ValueError(f"Agent ID {end_turn.agent_id} not found in delegates")


@dataclass(kw_only=True)
class OrchestrationContext:
    orchestrator: Orchestrator
    agent: Agent
