import inspect
from asyncio import CancelledError
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Optional, TypeVar

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
current_orchestrator: ContextVar["Orchestrator|None"] = ContextVar(
    "current_orchestrator",
    default=None,
)
RESULT_TOOL_PREFIX = "_EndTurn_"


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
    _token: Any = field(default=None, init=False, repr=False)

    def __post_init__(self):
        all_agents = {t.get_agent() for t in self.tasks}
        if self.agents:
            all_agents.update(self.agents)
        if len(all_agents) > 1:
            self.team = marvin.agents.team.Swarm(members=list(all_agents))
        else:
            agent = next(iter(all_agents))
            if isinstance(agent, marvin.agents.team.Team):
                self.team = agent
            else:
                self.team = marvin.agents.team.SoloTeam(members=[agent])

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
        active_tasks = [
            t for t in self.incomplete_tasks() if t.get_agent() in self.active_actors()
        ]

        # Mark tasks as running if they're pending
        for task in active_tasks:
            if task.is_pending():
                task.mark_running()
                await self.thread.add_user_message_async(f"Task started: {task}")

        self.team.start_turn()
        await self.handle_event(AgentStartTurnEvent(agent=self.team))

        # --- get tools
        tools = set()
        for t in active_tasks:
            tools.update(t.get_tools())
        tools = list(tools)

        # --- get end turn tools
        end_turn_tools = set()
        for t in active_tasks:
            end_turn_tools.update(t.get_end_turn_tools())
        if self.get_delegates():
            end_turn_tools.add(DelegateToAgent)
        end_turn_tools.update(self.team.get_end_turn_tools())
        end_turn_tools = list(end_turn_tools)

        # --- prepare messages
        orchestrator_prompt = OrchestratorPrompt(
            orchestrator=self,
            tasks=self.incomplete_tasks(),
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
        await self._record_messages(result)

        # --- end turn
        self.team.end_turn()
        await self.handle_event(AgentEndTurnEvent(agent=self.team))

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
            result_tool_name=RESULT_TOOL_PREFIX,
            result_tool_description="This tool will end your turn.",
            retries=marvin.settings.agent_retries,
        )
        agentlet.result_validator(self.validate_end_turn)

        for tool in agentlet._function_tools.values():
            original_run = tool.run

            # Wrap the tool run function to emit events for each call / result
            async def run(
                message: ToolCallPart,
                run_context: RunContext[AgentDeps],
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
            current = current.active_member

        return delegates

    async def _record_messages(self, result):
        for message in result.new_messages():
            for event in message_to_events(
                agent=self.team.active_member,
                message=message,
            ):
                await self.handle_event(event)
        await self.thread.add_messages_async(result.new_messages())

    def incomplete_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.is_incomplete()]

    async def run(self, raise_on_failure: bool = True) -> list[RunResult]:
        results = []
        token = current_orchestrator.set(self)
        try:
            with self.thread:
                await self.handle_event(OrchestratorStartEvent())

                try:
                    while self.incomplete_tasks():
                        result = await self._run_turn()
                        results.append(result)

                        if raise_on_failure:
                            if failed := next(
                                (t for t in self.incomplete_tasks() if t.is_failed()),
                                False,
                            ):
                                raise ValueError(f"Task {failed.id} failed")

                except (Exception, KeyboardInterrupt, CancelledError) as e:
                    await self.handle_event(OrchestratorExceptionEvent(error=str(e)))
                    raise
                finally:
                    await self.handle_event(OrchestratorEndEvent())

        finally:
            current_orchestrator.reset(token)

        return results

    async def validate_end_turn(self, result: EndTurn):
        if isinstance(result, EndTurn):
            try:
                await result.run(orchestrator=self)
            except Exception as e:
                logger.debug(f"End turn tool failed: {e}")
                raise pydantic_ai.ModelRetry(message=f"End turn tool failed: {e}")
        return result

    def active_team(self) -> marvin.agents.team.Team:
        """Returns the currently active team that contains the currently active agent."""
        active_team = self.team
        while not isinstance(active_team.active_member, Agent):
            active_team = active_team.active_member
        return active_team

    def active_agent(self) -> Agent:
        """Returns the currently active agent."""
        active_team = self.active_team()
        return active_team.active_member

    def active_actors(self) -> list[Actor]:
        """Returns a list of all active actors in the hierarchy, starting with the
        orchestrator's team and following the team hierarchy to the active
        agent.
        """
        actors = []
        actor = self.team
        while not isinstance(actor, Agent):
            actors.append(actor)
            actor = actor.active_member
        actors.append(actor)
        return actors

    def get_agent_tree(self) -> dict:
        """Returns a tree structure representing the hierarchy of teams and agents.

        Returns:
            dict: A nested dictionary where each team contains its agents, and agents are leaf nodes.
                 Format: {
                     "type": "team"|"agent",
                     "id": str,
                     "members": [...] # only present for teams
                 }

        """
        active_actors = self.active_actors()

        def _build_tree(node: Agent | marvin.agents.team.Team) -> dict:
            if isinstance(node, marvin.agents.team.Team):
                return {
                    # "type": "team",
                    "id": node.id,
                    "members": [_build_tree(agent) for agent in node.members],
                    "active": node in active_actors,
                }
            return {
                # "type": "agent",
                "id": node.id,
                "active": node in active_actors,
            }

        return _build_tree(self.team)

    @classmethod
    def get_current(cls) -> Optional["Orchestrator"]:
        """Get the current orchestrator from context."""
        return current_orchestrator.get()


def get_current_orchestrator() -> Orchestrator | None:
    """Get the currently active orchestrator from context.

    Returns:
        The current Orchestrator instance or None if no orchestrator is active.

    """
    return Orchestrator.get_current()
