import math
import os
from asyncio import CancelledError
from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, Sequence, TypeVar

from pydantic_ai.agent import AgentRunResult
from pydantic_ai.mcp import MCPServer, MCPServerStdio
from pydantic_ai.messages import UserContent

import marvin
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
from marvin.engine.streaming import handle_agentlet_events
from marvin.handlers import AsyncHandler, Handler
from marvin.handlers.print_handler import PrintHandler
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
                await handler._handle(event)
            else:
                handler._handle(event)

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

    async def run_once(
        self,
        actor: Actor | None = None,
        active_mcp_servers: list[MCPServer] | None = None,
    ) -> AgentRunResult:
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
        await self._check_memories(actor=actor, assigned_tasks=assigned_tasks)

        # --- get messages
        user_prompt, prompt_messages = await self._get_messages(
            actor=actor, assigned_tasks=assigned_tasks
        )

        # --- run agent, passing active_mcp_servers --- #
        agentlet = await actor.get_agentlet(
            tools=list(tools),
            end_turn_tools=list(end_turn_tools),
            active_mcp_servers=active_mcp_servers,
        )

        with actor:
            async with agentlet.iter(
                user_prompt,
                message_history=[m.message for m in prompt_messages],
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
            # skip the first message since we either pull it from history or
            # send an empty string
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
        if isinstance(result.output, EndTurn):
            await result.output.run(thread=self.thread, actor=actor)

        await actor.end_turn(result=result, thread=self.thread)
        await self.handle_event(ActorEndTurnEvent(actor=actor))

    @asynccontextmanager
    async def _manage_mcp_servers(
        self, actor: Actor
    ) -> AsyncIterator[list["MCPServer"]]:
        """Context manager to start and stop MCP servers for a given actor."""
        logger.debug(f"[_manage_mcp_servers] Preparing MCP servers for {actor.name}...")
        mcp_exit_stack = AsyncExitStack()
        active_servers: list["MCPServer"] = []
        servers_started = False

        # Check if actor has the method before calling
        if not hasattr(actor, "get_mcp_servers"):
            logger.debug(
                f"[_manage_mcp_servers] Actor {actor.name} does not have get_mcp_servers method."
            )
            yield active_servers  # Yield empty list if no servers
            return

        servers_to_manage = actor.get_mcp_servers()

        if not servers_to_manage:
            logger.debug(
                f"[_manage_mcp_servers] Actor {actor.name} has no configured MCP servers."
            )
            yield active_servers  # Yield empty list if no servers
            return

        logger.debug(
            f"[_manage_mcp_servers] Found {len(servers_to_manage)} server configurations."
        )
        for i, server in enumerate(servers_to_manage):
            logger.debug(
                f"[_manage_mcp_servers] Processing server #{i + 1}: {server!r}"
            )
            try:
                # Set environment variables for stdio servers if not already set
                if isinstance(server, MCPServerStdio) and server.env is None:
                    logger.debug(
                        f"[_manage_mcp_servers] Server #{i + 1} is MCPServerStdio with no env set. Setting env=dict(os.environ)."
                    )
                    # Use a copy of current environment
                    server.env = dict(os.environ)

                logger.debug(
                    f"[_manage_mcp_servers] Entering context for server #{i + 1}..."
                )
                # Enter the server's async context manager
                await mcp_exit_stack.enter_async_context(server)
                active_servers.append(
                    server
                )  # Add to active list *after* successful context entry
                logger.debug(
                    f"[_manage_mcp_servers] Context entered successfully for server #{i + 1}."
                )
                servers_started = True
            except Exception as e:
                logger.error(
                    f"[_manage_mcp_servers] Failed to start MCP server #{i + 1} ({server!r}): {e}",
                    exc_info=True,
                )
                # Optionally re-raise or handle specific errors? For now, just log.

        if servers_started:
            logger.debug(
                f"[_manage_mcp_servers] Yielding control with {len(active_servers)} active servers."
            )
        else:
            logger.debug(
                "[_manage_mcp_servers] No servers were successfully started, yielding control."
            )

        try:
            yield active_servers  # Yield the list of successfully started servers
        finally:
            logger.debug("[_manage_mcp_servers] Cleaning up MCP servers...")
            # The AsyncExitStack handles closing all entered contexts properly
            await mcp_exit_stack.aclose()
            logger.debug("[_manage_mcp_servers] MCP server cleanup complete.")

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

                # --- Determine primary actor (simplistic for now) --- #
                # TODO: Handle multi-actor scenarios properly
                actor = self.tasks[0].get_actor() if self.tasks else None
                if not actor:
                    raise ValueError("Cannot run orchestrator without tasks/actors.")
                # ------------------------------------------------------

                # --- Wrap the main loop with the MCP server manager --- #
                async with self._manage_mcp_servers(actor) as active_mcp_servers:
                    logger.debug(
                        f"Orchestrator loop starting with {len(active_mcp_servers)} active MCP servers."
                    )
                    try:
                        turns = 0

                        while incomplete_tasks and (
                            max_turns is None or turns < max_turns
                        ):
                            # Pass active_mcp_servers to run_once
                            result = await self.run_once(
                                actor=actor, active_mcp_servers=active_mcp_servers
                            )
                            results.append(result)
                            turns += 1

                            # Handle potential failures
                            if raise_on_failure:
                                for task in self.tasks:
                                    if task.is_failed() and task in incomplete_tasks:
                                        raise ValueError(
                                            f"{task.friendly_name()} failed: {task.result}"
                                        )
                            # Update incomplete tasks status
                            incomplete_tasks = {
                                t for t in self.tasks if t.is_incomplete()
                            }

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

    async def _check_memories(
        self, actor: Actor, assigned_tasks: list[Task[Any]]
    ) -> None:
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

    async def _get_messages(
        self, actor: Actor, assigned_tasks: list[Task[Any]]
    ) -> tuple[str | Sequence[UserContent], list[Message]]:
        system_prompt = await self.thread.add_system_message_async(
            SystemPrompt(
                actor=actor,
                instructions=get_instructions(),
                tasks=assigned_tasks,
            ).render()
        )

        message_history = await self.thread.get_messages_async(
            include_system_messages=False
        )

        # attempt to extract the user message from the last message, if it represents a user prompt
        if (
            message_history
            and message_history[-1].message.kind == "request"
            and message_history[-1].message.parts[0].part_kind == "user-prompt"
        ):
            message_history, user_prompt = (
                message_history[:-1],
                message_history[-1].message.parts[0].content,
            )

        # otherwise, use a minimal viable user prompt. Pydantic AI requires a
        # user prompt and some providers do not allow empty prompts.
        else:
            user_prompt = " "

        return user_prompt, [system_prompt] + message_history

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
