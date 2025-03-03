import math
from asyncio import CancelledError
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, TypeVar

from pydantic_ai.agent import AgentRunResult

import marvin
import marvin.agents.team
import marvin.engine.llm
from marvin.agents.actor import Actor
from marvin.agents.agent import Agent
from marvin.database import DBLLMCall
from marvin.engine.end_turn import EndTurn
from marvin.engine.events import (
    ActorEndTurnEvent,
    ActorStartTurnEvent,
    Event,
    OrchestratorEndEvent,
    OrchestratorErrorEvent,
    OrchestratorStartEvent,
)
from marvin.engine.handlers import AsyncHandler, Handler
from marvin.engine.print_handler import PrintHandler
from marvin.engine.streaming import handle_agentlet_events
from marvin.instructions import get_instructions
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.tasks.task import Task
from marvin.thread import Message, Thread, get_thread
from marvin.utilities.logging import get_logger

T = TypeVar("T")

logger = get_logger(__name__)

# Global context var for current orchestrator
_current_orchestrator: ContextVar["Orchestrator|None"] = ContextVar(
    "current_orchestrator",
    default=None,
)


@dataclass(kw_only=True)
class SystemPrompt(Template):
    source: str | Path = Path("system.jinja")

    actor: Actor
    instructions: list[str]
    tasks: list[Task]


@dataclass(kw_only=True)
class Orchestrator:
    tasks: list[Task[Any]]
    thread: Thread
    handlers: list[Handler | AsyncHandler]

    def __init__(
        self,
        tasks: list[Task[Any]],
        thread: Thread | str | None = None,
        handlers: list[Handler | AsyncHandler] | None = None,
    ):
        self.tasks = tasks
        self.thread = get_thread(thread)

        if handlers is None:
            if marvin.settings.enable_default_print_handler:
                handlers = [PrintHandler()]
            else:
                handlers = []
        self.handlers = handlers

    async def handle_event(self, event: Event):
        if marvin.settings.log_events:
            logger.debug(f"Handling event: {event.__class__.__name__}\n{event}")

        for handler in self.handlers:
            if isinstance(handler, AsyncHandler):
                await handler.handle(event)
            else:
                handler.handle(event)

    def get_all_tasks(
        self, filter: Literal["incomplete", "ready"] | None = None
    ) -> list[Task[Any]]:
        """Get all tasks, optionally filtered by status.

        Filters:
            - incomplete: tasks that are not yet complete
            - ready: tasks that are ready to be run
        """
        all_tasks: set[Task[Any]] = set()
        ordered_tasks: list[Task[Any]] = []

        def collect_tasks(task: Task[Any]) -> None:
            if task in all_tasks:
                return

            all_tasks.add(task)

            # collect subtasks
            for subtask in task.subtasks:
                collect_tasks(subtask)

            # collect dependencies
            for dep in task.depends_on:
                collect_tasks(dep)

            # add this task after its dependencies
            ordered_tasks.append(task)

            # collect parent
            if task.parent:
                collect_tasks(task.parent)

        for task in self.tasks:
            collect_tasks(task)

        if filter == "incomplete":
            return [t for t in ordered_tasks if t.is_incomplete()]
        elif filter == "ready":
            return [t for t in ordered_tasks if t.is_ready()]
        elif filter:
            raise ValueError(f"Invalid filter: {filter}")
        return ordered_tasks

    async def run_once(self, actor: Actor | None = None) -> AgentRunResult:
        tasks = self.get_all_tasks(filter="ready")

        if not tasks:
            raise ValueError("No tasks to run")

        if actor is None:
            actor = tasks[0].get_actor()

        assigned_tasks = [t for t in tasks if actor is t.get_actor()]

        # Mark tasks as running if they're pending
        for task in assigned_tasks:
            if task.is_pending():
                await task.mark_running(thread=self.thread)
        await self.start_turn(actor=actor)

        # --- get tools
        tools: set[Callable[..., Any]] = set()
        for t in assigned_tasks:
            tools.update(t.get_tools())

        # --- get end turn tools
        end_turn_tools: set[EndTurn] = set()
        for t in assigned_tasks:
            end_turn_tools.update(t.get_end_turn_tools())

        # --- get memories
        memories: set[Memory] = set()
        for t in assigned_tasks:
            memories.update([m for m in t.memories if m.auto_use])
        if isinstance(actor, Agent):
            memories.update([m for m in actor.get_memories() if m.auto_use])
        if memories:
            memory_messages = await self.thread.get_messages_async(limit=3)
            # Import here to avoid circular import
            from marvin.thread import message_adapter

            query = message_adapter.dump_json(memory_messages).decode()
            for memory in memories:
                memory_result = {
                    memory.friendly_name(): await memory.search(query=query, n=3)
                }
                await self.thread.add_info_message_async(
                    memory_result,
                    prefix="Automatically recalled memories",
                )

        system_prompt = await self.thread.add_system_message_async(
            SystemPrompt(
                actor=actor,
                instructions=get_instructions(),
                tasks=assigned_tasks,
            ).render()
        )

        messages = await self.thread.get_messages_async(include_system_messages=False)
        prompt_messages: list[Message] = [system_prompt] + messages

        # --- run agent
        agentlet = await actor.get_agentlet(
            tools=list(tools),
            end_turn_tools=list(end_turn_tools),
        )

        with actor:
            with agentlet.iter(
                user_prompt="", message_history=[m.message for m in prompt_messages]
            ) as run:
                async for event in handle_agentlet_events(
                    agentlet=agentlet,
                    actor=actor,
                    run=run,
                ):
                    await self.handle_event(event)

        # --- add final messages to the thread
        new_messages = run.result.new_messages()
        completion_messages = await self.thread.add_messages_async(
            # skip the first message since we send an empty string
            new_messages[1:]
        )

        await DBLLMCall.create(
            thread_id=self.thread.id,
            usage=run.usage(),
            prompt_messages=prompt_messages,
            completion_messages=completion_messages,
        )

        # --- end turn
        await self.end_turn(result=run.result, actor=actor)

        return run

    async def start_turn(self, actor: Actor):
        await actor.start_turn(thread=self.thread)
        await self.handle_event(ActorStartTurnEvent(actor=actor))

    async def end_turn(self, result: AgentRunResult, actor: Actor):
        if isinstance(result.data, EndTurn):
            await result.data.run(thread=self.thread, actor=actor)

        await actor.end_turn(result=result, thread=self.thread)
        await self.handle_event(ActorEndTurnEvent(actor=actor))

    async def run(
        self,
        raise_on_failure: bool = True,
        max_turns: int | float | None = None,
    ) -> list[AgentRunResult]:
        if max_turns is None:
            max_turns = marvin.settings.max_agent_turns
        if max_turns is None:
            max_turns = math.inf

        results: list[AgentRunResult] = []
        incomplete_tasks: set[Task[Any]] = {t for t in self.tasks if t.is_incomplete()}
        token = _current_orchestrator.set(self)
        try:
            with self.thread:
                await self.handle_event(OrchestratorStartEvent())

                try:
                    turns = 0
                    actor = None

                    # the while loop continues until all the tasks that were
                    # provided to the orchestrator are complete OR max turns is
                    # reached. Note this is not the same as checking *every*
                    # task that `get_all_tasks()` returns. If a task has
                    # incomplete dependencies, they will be evaluated as part of
                    # the orchestrator logic, but not considered part of the
                    # termination condition.
                    while incomplete_tasks and (max_turns is None or turns < max_turns):
                        result = await self.run_once(actor=actor)
                        results.append(result)
                        turns += 1

                        if raise_on_failure:
                            for task in self.tasks:
                                if task.is_failed() and task in incomplete_tasks:
                                    raise ValueError(
                                        f"{task.friendly_name()} failed: {task.result}"
                                    )
                        incomplete_tasks = {t for t in self.tasks if t.is_incomplete()}

                    if max_turns and turns >= max_turns:
                        raise ValueError("Max agent turns reached")

                except (Exception, KeyboardInterrupt, CancelledError) as e:
                    await self.handle_event(OrchestratorErrorEvent(error=str(e)))
                    raise
                finally:
                    await self.handle_event(OrchestratorEndEvent())

        finally:
            _current_orchestrator.reset(token)

        return results

    @classmethod
    def get_current(cls) -> Optional["Orchestrator"]:
        """Get the current orchestrator from context."""
        return _current_orchestrator.get()


def get_current_orchestrator() -> Orchestrator | None:
    """Get the currently active orchestrator from context.

    Returns:
        The current Orchestrator instance or None if no orchestrator is active.

    """
    return Orchestrator.get_current()
