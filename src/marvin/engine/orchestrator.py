import math
from asyncio import CancelledError
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, TypeVar

from pydantic_ai._parts_manager import ModelResponsePartsManager
from pydantic_ai.agent import Agent as PydanticAgentlet
from pydantic_ai.agent import AgentRun, AgentRunResult
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelResponsePart,
    PartDeltaEvent,
    PartStartEvent,
    RetryPromptPart,
    TextPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
    ToolReturnPart,
)

import marvin
import marvin.agents.team
import marvin.engine.llm
from marvin.agents.actor import Actor
from marvin.agents.agent import Agent
from marvin.database import DBLLMCall
from marvin.engine.end_turn import EndTurn
from marvin.engine.events import (
    ActorEndTurnEvent,
    ActorMessageDeltaEvent,
    ActorStartTurnEvent,
    EndTurnToolCallEvent,
    Event,
    OrchestratorEndEvent,
    OrchestratorExceptionEvent,
    OrchestratorStartEvent,
    ToolCallDeltaEvent,
    ToolCallEvent,
    ToolResultEvent,
    ToolRetryEvent,
    UserMessageEvent,
)
from marvin.engine.handlers import AsyncHandler, Handler
from marvin.engine.print_handler import PrintHandler
from marvin.instructions import get_instructions
from marvin.memory.memory import Memory
from marvin.prompts import Template
from marvin.tasks.task import Task
from marvin.thread import Thread, get_thread
from marvin.utilities.logging import get_logger

T = TypeVar("T")

logger = get_logger(__name__)

# Global context var for current orchestrator
_current_orchestrator: ContextVar["Orchestrator|None"] = ContextVar(
    "current_orchestrator",
    default=None,
)


async def handle_agentlet_events(
    actor: Actor,
    run: AgentRun,
    end_turn_tools: list[EndTurn],
):
    """Run a PydanticAI agentlet and process its events through the Marvin event system.

    This function:
    1. Runs the agentlet's iterator
    2. Processes all nodes and events from PydanticAI
    3. Converts them to Marvin events and yields them

    Args:
        run: The agentlet run to process
        actor: The actor associated with this agentlet run

    Yields:
        Marvin events derived from PydanticAI events
    """
    # Create a parts manager to accumulate delta events for this run
    parts_manager = ModelResponsePartsManager()
    end_turn_tool_names = {t.__name__ for t in end_turn_tools}

    def _get_snapshot(index: int) -> ModelResponsePart:
        return parts_manager.get_parts()[index]

    # Private helper function to process PydanticAI events
    def _process_pydantic_event(event) -> Event | None:
        # Handle Part Start Events
        if isinstance(event, PartStartEvent):
            # Process a new part starting
            if event.part.part_kind == "text":
                # For text parts, update the parts manager
                parts_manager.handle_text_delta(
                    vendor_part_id=event.index, content=event.part.content
                )

                # Only emit delta events for streaming updates
                return ActorMessageDeltaEvent(
                    actor=actor,
                    delta=TextPartDelta(content_delta=event.part.content),
                    snapshot=_get_snapshot(event.index),
                )

            elif event.part.part_kind == "tool-call":
                # For tool call parts
                parts_manager.handle_tool_call_part(
                    vendor_part_id=event.index,
                    tool_name=event.part.tool_name,
                    args=event.part.args,
                    tool_call_id=event.part.tool_call_id,
                )

                # Always emit delta events for streaming updates
                snapshot = _get_snapshot(event.index)
                return ToolCallDeltaEvent(
                    actor=actor,
                    delta=ToolCallPartDelta(
                        tool_name_delta=event.part.tool_name,
                        args_delta=event.part.args,
                        tool_call_id=event.part.tool_call_id,
                    ),
                    snapshot=snapshot,
                    tool_call_id=snapshot.tool_call_id,
                )

        # Handle Part Delta Events
        elif isinstance(event, PartDeltaEvent):
            # Process a delta update to an existing part
            if isinstance(event.delta, TextPartDelta):
                # Handle text delta
                parts_manager.handle_text_delta(
                    vendor_part_id=event.index, content=event.delta.content_delta
                )

                # Emit delta event for streaming
                return ActorMessageDeltaEvent(
                    actor=actor,
                    delta=event.delta,
                    snapshot=_get_snapshot(event.index),
                )

            elif isinstance(event.delta, ToolCallPartDelta):
                # Handle tool call delta
                parts_manager.handle_tool_call_delta(
                    vendor_part_id=event.index,
                    tool_name=event.delta.tool_name_delta,
                    args=event.delta.args_delta,
                    tool_call_id=event.delta.tool_call_id,
                )
                # Emit delta event for streaming
                return ToolCallDeltaEvent(
                    actor=actor,
                    delta=event.delta,
                    snapshot=_get_snapshot(event.index),
                    tool_call_id=event.delta.tool_call_id,
                )

        # Handle Function Tool Call Events
        elif isinstance(event, FunctionToolCallEvent):
            # This is the signal that a tool call is complete and ready to be executed
            # Emit tool call complete event
            return ToolCallEvent(
                actor=actor,
                message=event.part,
                tool_call_id=event.part.tool_call_id,
            )

        # Handle Function Tool Result Events
        elif isinstance(event, FunctionToolResultEvent):
            # Emit tool result event
            if isinstance(event.result, ToolReturnPart):
                return ToolResultEvent(message=event.result)
            elif isinstance(event.result, RetryPromptPart):
                return ToolRetryEvent(message=event.result)
            else:
                pass

        # Handle Final Result Event
        # This fires as soon as Pydantic AI recognizes that the tool call is an end turn tool
        # (i.e. as soon as the name is recognized, but before the args are returned)
        elif isinstance(event, FinalResultEvent):
            # find a matching tool call event
            tool_call_part = next(
                (
                    p
                    for p in parts_manager.get_parts()
                    if isinstance(p, ToolCallPart) and p.tool_name == event.tool_name
                ),
                None,
            )
            if tool_call_part is None:
                raise ValueError(
                    f"No tool call part found for {event.tool_name}. This is unexpected."
                )

            return EndTurnToolCallEvent(
                actor=actor,
                event=event,
                tool_call_id=tool_call_part.tool_call_id,
            )

        else:
            raise ValueError(f"Unknown event type: {type(event)}")

    async for node in run:
        if PydanticAgentlet.is_user_prompt_node(node):
            yield UserMessageEvent(
                message=node.user_prompt,
            )

        elif PydanticAgentlet.is_model_request_node(node):
            # EndTurnTool retries do not get processed as normal
            # FunctionToolResultEvents, but can be detected by checking for
            # RetryPromptPart that match the end turn tool names. Here, we
            # yield a ToolRetryEvent for each RetryPromptPart that matches an
            # end turn tool name.
            for part in node.request.parts:
                if (
                    isinstance(part, RetryPromptPart)
                    and part.tool_name in end_turn_tool_names
                ):
                    yield ToolRetryEvent(message=part)

            # Model request node - stream tokens from the model's request
            async with node.stream(run.ctx) as request_stream:
                async for event in request_stream:
                    try:
                        event = _process_pydantic_event(event)
                        if event:
                            yield event

                    except Exception as e:
                        # Log any errors that occur during event processing
                        logger.error(
                            f"Error processing pydantic event {type(event).__name__}: {e}"
                        )
                        # Provide detailed traceback in debug mode
                        if marvin.settings.log_level == "DEBUG":
                            logger.exception("Detailed traceback:")

        elif PydanticAgentlet.is_handle_response_node(node):
            # Handle-response node - the model returned data, potentially calls a tool
            async with node.stream(run.ctx) as handle_stream:
                async for event in handle_stream:
                    try:
                        event = _process_pydantic_event(event)
                        if event:
                            yield event

                    except Exception as e:
                        # Log any errors that occur during event processing
                        logger.error(
                            f"Error processing pydantic event {type(event).__name__}: {e}"
                        )
                        # Provide detailed traceback in debug mode
                        if marvin.settings.log_level == "DEBUG":
                            logger.exception("Detailed traceback:")

        # Check if we've reached the final End node
        elif PydanticAgentlet.is_end_node(node):
            pass
        else:
            pass


@dataclass(kw_only=True)
class OrchestratorPrompt(Template):
    source: str | Path = Path("orchestrator.jinja")

    orchestrator: "Orchestrator"
    actor: Actor
    tasks: list[Task[Any]]
    instructions: list[str]
    end_turn_tools: list[EndTurn]


@dataclass(kw_only=True)
class Orchestrator:
    tasks: list[Task[Any]]
    thread: Thread | str | None = None
    handlers: list[Handler | AsyncHandler] | None = None

    def __post_init__(self):
        self.thread = get_thread(self.thread)
        if self.handlers is None:
            if marvin.settings.enable_default_print_handler:
                self.handlers = [PrintHandler()]
            else:
                self.handlers = []

    async def handle_event(self, event: Event):
        if marvin.settings.log_events:
            logger.debug(f"Handling event: {event.__class__.__name__}\n{event}")

        for handler in self.handlers or []:
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

        await self.thread.add_info_message_async(
            f"Active actor: {actor.friendly_name()}"
        )

        assigned_tasks = [t for t in tasks if actor is t.get_actor()]

        # Mark tasks as running if they're pending
        for task in assigned_tasks:
            if task.is_pending():
                task.mark_running()
                await self.thread.add_info_message_async(
                    f"Task started: {task.friendly_name()}"
                )

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
            from marvin.thread import (
                message_adapter,  # Import here to avoid circular import
            )

            query = message_adapter.dump_json(memory_messages).decode()
            for memory in memories:
                memory_result = {
                    memory.friendly_name(): await memory.search(query=query, n=3)
                }
                await self.thread.add_info_message_async(
                    f"Automatically recalled memories: {memory_result}"
                )

        orchestrator_prompt = OrchestratorPrompt(
            orchestrator=self,
            actor=actor,
            tasks=assigned_tasks,
            instructions=get_instructions(),
            end_turn_tools=end_turn_tools,
        ).render()

        messages = await self.thread.get_messages_async()

        all_messages = [
            marvin.engine.llm.SystemMessage(content=orchestrator_prompt),
        ] + messages

        # --- run agent
        agentlet = await actor.get_agentlet(
            messages=all_messages,
            tools=list(tools),
            end_turn_tools=list(end_turn_tools),
        )

        # Run the agentlet with our new function
        with actor:
            with agentlet.iter("", message_history=all_messages) as run:
                async for event in handle_agentlet_events(
                    actor=actor, run=run, end_turn_tools=list(end_turn_tools)
                ):
                    await self.handle_event(event)

        # Record the LLM call in the database
        llm_call = await DBLLMCall.create(
            thread_id=self.thread.id,
            usage=run.usage(),
        )

        # --- add final messages to the thread
        await self.thread.add_messages_async(
            run.result.new_messages(), llm_call_id=llm_call.id
        )

        # --- end turn
        await self.end_turn(result=run.result, actor=actor)

        return run

    async def start_turn(self, actor: Actor):
        await actor.start_turn(orchestrator=self)
        await self.handle_event(ActorStartTurnEvent(actor=actor))

    async def end_turn(self, result: AgentRunResult, actor: Actor):
        if isinstance(result.data, EndTurn):
            await result.data.run(orchestrator=self, actor=actor)

        await actor.end_turn(result=result, orchestrator=self)
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
                    await self.handle_event(OrchestratorExceptionEvent(error=str(e)))
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
