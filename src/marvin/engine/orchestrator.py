import inspect
import math
from asyncio import CancelledError
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Literal, Optional, TypeVar

import pydantic_ai
from pydantic_ai.messages import ModelRequestPart, RetryPromptPart, ToolCallPart
from pydantic_ai.result import AgentDeps, RunContext, RunResult

import marvin
import marvin.agents.team
import marvin.engine.llm
from marvin.agents.actor import Actor
from marvin.agents.agent import Agent
from marvin.engine.end_turn import DelegateToAgent, EndTurn
from marvin.engine.events import (
    AgentEndTurnEvent,
    AgentStartTurnEvent,
    Event,
    OrchestratorEndEvent,
    OrchestratorExceptionEvent,
    OrchestratorStartEvent,
    ToolCallEvent,
    ToolRetryEvent,
    ToolReturnEvent,
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

# Global context var for current orchestrator
_current_orchestrator: ContextVar["Orchestrator|None"] = ContextVar(
    "current_orchestrator",
    default=None,
)


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
    agents: list[Actor] = None
    thread: Thread
    handlers: list[Handler | AsyncHandler] = None

    team: marvin.agents.team.Team = field(init=False, repr=False)
    _staged_delegate: tuple[marvin.agents.team.Team, Actor] | None = field(
        default=None, init=False, repr=False
    )
    _token: Any = field(default=None, init=False, repr=False)

    def __post_init__(self):
        all_agents = {t.get_agent() for t in self.tasks}
        if self.agents:
            all_agents.update(self.agents)
        if len(all_agents) > 1:
            self.team = marvin.agents.team.Swarm(agents=list(all_agents))
        else:
            agent = next(iter(all_agents))
            if isinstance(agent, marvin.agents.team.Team):
                self.team = agent
            else:
                self.team = marvin.agents.team.SoloTeam(agents=[agent])

        self.thread = get_thread(self.thread)
        if self.handlers is None:
            if marvin.settings.enable_default_print_handler:
                self.handlers = [PrintHandler()]
            else:
                self.handlers = []

    async def handle_event(self, event: Event):
        if marvin.settings.log_events:
            logger.debug(f"Handling event: {event.__class__.__name__}\n{event}")

        for handler in self.handlers:
            if isinstance(handler, AsyncHandler):
                await handler.handle(event)
            else:
                handler.handle(event)

    async def _run_turn(self):
        # Get tasks for the current active agent
        tasks = self.get_all_tasks(filter="assigned")

        # Mark tasks as running if they're pending
        for task in tasks:
            if task.is_pending():
                task.mark_running()
                await self.thread.add_user_message_async(
                    f"Task started: {task.friendly_name()}"
                )

        self.team.start_turn()
        await self.handle_event(AgentStartTurnEvent(agent=self.team))

        # --- get tools
        tools = set()
        for t in tasks:
            tools.update(t.get_tools())
        tools = list(tools)

        # --- get end turn tools
        end_turn_tools = set()

        for t in tasks:
            end_turn_tools.update(t.get_end_turn_tools())

        if self.get_delegates():
            end_turn_tools.add(DelegateToAgent)
        end_turn_tools.update(self.team.get_end_turn_tools())
        end_turn_tools = list(end_turn_tools)

        # --- prepare messages
        orchestrator_prompt = OrchestratorPrompt(
            orchestrator=self,
            tasks=self.get_all_tasks(),
            instructions=get_instructions(),
            end_turn_tools=end_turn_tools,
        ).render()

        messages = await self.thread.get_messages_async()
        all_messages = [
            marvin.engine.llm.SystemMessage(content=orchestrator_prompt),
        ] + messages

        # --- run agent
        agentlet = self._get_agentlet(tools=tools, end_turn_tools=end_turn_tools)

        result = await agentlet.run("", message_history=all_messages)

        # --- record messages
        for message in result.new_messages():
            for event in message_to_events(
                agent=self.team.active_agent,
                message=message,
                agentlet=agentlet,
            ):
                await self.handle_event(event)
        await self.thread.add_messages_async(result.new_messages())

        # --- end turn
        self.end_turn()
        await self.handle_event(AgentEndTurnEvent(agent=self.team))

        for task in tasks:
            if task.is_successful():
                await self.thread.add_user_message_async(
                    f"Task completed: {task.friendly_name()}"
                )
            elif task.is_failed():
                await self.thread.add_user_message_async(
                    f"Task failed: {task.friendly_name()}"
                )

        return result

    def _get_agentlet(self, tools: list, end_turn_tools: list) -> Any:
        """Get an agentlet with wrapped tools and configured result validator.

        Args:
            tools: List of tools to provide to the agentlet
            end_turn_tools: List of end turn tools to provide to the agentlet

        Returns:
            The configured agentlet

        """

        # Pydantic AI doesn't catch errors except for ModelRetry, so we need to make sure we catch them
        # ourselves and raise a ModelRetry.
        def wrap_tool(tool: Callable[..., Any]):
            if inspect.iscoroutinefunction(tool):

                @wraps(tool)
                async def _fn(*args, **kwargs):
                    try:
                        return await tool(*args, **kwargs)
                    except (
                        pydantic_ai.ModelRetry,
                        KeyboardInterrupt,
                        CancelledError,
                    ) as e:
                        logger.debug(f"Tool failed: {e}")
                        raise e
                    except Exception as e:
                        logger.debug(f"Tool failed: {e}")
                        raise pydantic_ai.ModelRetry(message=f"Tool failed: {e}") from e

                return _fn

            @wraps(tool)
            def _fn(*args, **kwargs):
                try:
                    return tool(*args, **kwargs)
                except (
                    pydantic_ai.ModelRetry,
                    KeyboardInterrupt,
                    CancelledError,
                ) as e:
                    logger.debug(f"Tool failed: {e}")
                    raise e
                except Exception as e:
                    logger.debug(f"Tool failed: {e}")
                    raise pydantic_ai.ModelRetry(message=f"Tool failed: {e}") from e

            return _fn

        tools = [wrap_tool(tool) for tool in tools]

        agentlet = self.team.get_agentlet(
            tools=tools,
            result_types=end_turn_tools,
            result_tool_name="EndTurn",
            result_tool_description="This tool will end your turn.",
            retries=marvin.settings.agent_retries,
        )

        @agentlet.result_validator
        async def validate_end_turn(result: EndTurn):
            if isinstance(result, EndTurn):
                try:
                    await result.run(orchestrator=self)
                except pydantic_ai.ModelRetry as e:
                    raise e
                except Exception as e:
                    logger.debug(f"End turn tool failed: {e}")
                    raise pydantic_ai.ModelRetry(message=f"End turn tool failed: {e}")

            # return the original result
            return result

        for tool in agentlet._function_tools.values():
            # Wrap the tool run function to emit events for each call / result
            async def run(
                message: ToolCallPart,
                run_context: RunContext[AgentDeps],
                # pass as arg to avoid late binding issues
                original_run: Callable[..., Any] = tool.run,
            ) -> ModelRequestPart:
                await self.handle_event(
                    ToolCallEvent(agent=self.active_agent(), message=message),
                )
                result = await original_run(message, run_context)
                if isinstance(result, RetryPromptPart):
                    await self.handle_event(ToolRetryEvent(message=result))
                else:
                    await self.handle_event(ToolReturnEvent(message=result))
                return result

            tool.run = run

        return agentlet

    def get_delegates(self) -> list[Actor]:
        delegates = []
        current = self.team

        # Follow active_agent chain, collecting delegates at each level
        while isinstance(current, marvin.agents.team.Team):
            delegates.extend(current.get_delegates())
            current = current.active_agent

        return delegates

    def stage_delegate(self, agent_id: str) -> None:
        """
        Stage a delegation to another agent. The delegation will be applied at
        the end of the turn. This allows all messages created during the turn to
        be properly attributed to the currently active agent, without confusion
        about whether the new delegate was active.

        Validates the agent_id and stores the team/agent pair that will be
        updated at the end of the turn.
        """
        delegates = {d.id: d for d in self.get_delegates()}
        if agent_id not in delegates:
            raise ValueError(f"Agent ID {agent_id} not found in delegates")

        logger.debug(
            f"{self.active_agent().friendly_name()}: Delegating to {delegates[agent_id].friendly_name()}",
        )

        # walk active_agents to find the delegate
        current = self.team
        while agent_id not in {a.id for a in current.agents}:
            if not isinstance(current, marvin.agents.team.Team):
                raise ValueError(f"Agent ID {agent_id} not found in delegates")
            current = current.active_agent

        agent = next(a for a in current.agents if a.id == agent_id)
        self._staged_delegate = (current, agent)

    def end_turn(self) -> None:
        """End the current turn, applying any staged delegation and notifying the team."""
        if self._staged_delegate is not None:
            team, agent = self._staged_delegate
            team.active_agent = agent
            self._staged_delegate = None
        self.team.end_turn()

    def get_all_tasks(
        self, filter: Literal["incomplete", "ready", "assigned"] | None = None
    ) -> list[Task]:
        """Get all tasks, optionally filtered by status.

        Filters:
            - incomplete: tasks that are not yet complete
            - ready: tasks that are ready to be run
            - assigned: tasks that are ready and assigned to the active agents
        """
        all_tasks: set[Task] = set()
        ordered_tasks: list[Task] = []

        def collect_tasks(task: Task) -> list[Task]:
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
        elif filter == "assigned":
            return [
                t
                for t in ordered_tasks
                if t.is_ready() and t.get_agent() in self.active_actors()
            ]
        elif filter:
            raise ValueError(f"Invalid filter: {filter}")
        return ordered_tasks

    async def run(
        self, raise_on_failure: bool = True, max_turns: int | None = None
    ) -> list[RunResult]:
        if max_turns is None:
            max_turns = marvin.settings.max_agent_turns
        if max_turns is None:
            max_turns = math.inf

        results = []
        incomplete_tasks: set[Task] = {t for t in self.tasks if t.is_incomplete()}
        token = _current_orchestrator.set(self)
        try:
            with self.thread:
                await self.handle_event(OrchestratorStartEvent())

                try:
                    turns = 0

                    # the while loop continues until all the tasks that were
                    # provided to the orchestrator are complete OR max turns is
                    # reached. Note this is not the same as checking *every*
                    # task that `get_all_tasks()` returns. If a task has
                    # incomplete dependencies, they will be evaluated as part of
                    # the orchestrator logic, but not considered part of the
                    # termination condition.
                    while incomplete_tasks and turns < max_turns:
                        result = await self._run_turn()
                        results.append(result)
                        turns += 1

                        if raise_on_failure:
                            for task in self.tasks:
                                if task.is_failed() and task in incomplete_tasks:
                                    raise ValueError(
                                        f"{task.friendly_name()} failed: {task.result}"
                                    )
                        incomplete_tasks = {t for t in self.tasks if t.is_incomplete()}

                    if turns >= max_turns:
                        raise ValueError("Max agent turns reached")

                except (Exception, KeyboardInterrupt, CancelledError) as e:
                    await self.handle_event(OrchestratorExceptionEvent(error=str(e)))
                    raise
                finally:
                    await self.handle_event(OrchestratorEndEvent())

        finally:
            _current_orchestrator.reset(token)

        return results

    def active_team(self) -> marvin.agents.team.Team:
        """Returns the currently active team that contains the currently active agent."""
        active_team = self.team
        while not isinstance(active_team.active_agent, Agent):
            active_team = active_team.active_agent
        return active_team

    def active_agent(self) -> Agent:
        """Returns the currently active agent."""
        active_team = self.active_team()
        return active_team.active_agent

    def active_actors(self) -> list[Actor]:
        """Returns a list of all active actors in the hierarchy, starting with the
        orchestrator's team and following the team hierarchy to the active
        agent.
        """
        actors = []
        actor = self.team
        while not isinstance(actor, Agent):
            actors.append(actor)
            actor = actor.active_agent
        actors.append(actor)
        return actors

    def get_agent_tree(self) -> dict:
        """Returns a tree structure representing the hierarchy of teams and agents.

        Returns:
            dict: A nested dictionary where each team contains its agents, and agents are leaf nodes.
                 Format: {
                     "type": "team"|"agent",
                     "id": str,
                     "agents": [...] # only present for teams
                 }

        """
        active_actors = self.active_actors()

        def _build_tree(node: Agent | marvin.agents.team.Team) -> dict:
            if isinstance(node, marvin.agents.team.Team):
                return {
                    "type": "team",
                    "id": node.id,
                    "agents": [_build_tree(agent) for agent in node.agents],
                    "active": node in active_actors,
                }
            return {
                "type": "agent",
                "id": node.id,
                "active": node in active_actors,
            }

        return _build_tree(self.team)

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
