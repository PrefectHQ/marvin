from collections.abc import Callable
from typing import Any

import pydantic_ai
from pydantic_ai._parts_manager import ModelResponsePartsManager
from pydantic_ai.agent import AgentRun
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
from pydantic_ai.tools import Tool

import marvin
import marvin.agents.team
import marvin.engine.llm
from marvin.agents.actor import Actor
from marvin.engine.end_turn import EndTurn
from marvin.engine.events import (
    ActorMessageDeltaEvent,
    EndTurnToolCallEvent,
    EndTurnToolResultEvent,
    Event,
    ToolCallDeltaEvent,
    ToolCallEvent,
    ToolResultEvent,
    ToolRetryEvent,
    UserMessageEvent,
)
from marvin.utilities.logging import get_logger

logger = get_logger(__name__)


async def handle_agentlet_events(
    agentlet: pydantic_ai.Agent,
    actor: Actor,
    run: AgentRun,
):
    """Run a PydanticAI agentlet and process its events through the Marvin event system.

    This function:
    1. Runs the agentlet's iterator
    2. Processes all nodes and events from PydanticAI
    3. Converts them to Marvin events and yields them

    Args:
        run: The agentlet run to process
        actor: The actor associated with this agentlet run

    Usage:

    agentlet = pydantic_ai.Agent(...)
    with agentlet.iter(msg) as run:
        async for event in handle_agentlet_events(
            actor=actor,
            run=run,
            tools=tools,
            end_turn_tools=end_turn_tools,
        ):
            yield event

    Yields:
        Marvin events derived from PydanticAI events
    """
    # Create a parts manager to accumulate delta events for this run
    parts_manager = ModelResponsePartsManager()
    tools_map = {}
    for t_tool_obj in agentlet._marvin_tools:
        if isinstance(t_tool_obj, Tool):
            tools_map[t_tool_obj.name] = t_tool_obj
        elif callable(t_tool_obj):
            tools_map[t_tool_obj.__name__] = t_tool_obj
        else:
            logger.warning(
                f"Encountered non-Tool, non-callable item in agentlet._marvin_tools: {type(t_tool_obj)}"
            )

    end_turn_tools_map = {}
    for t in agentlet._marvin_end_turn_tools:
        end_turn_tools_map[t.__name__] = t
        end_turn_tools_map[f"{agentlet._deprecated_result_tool_name}_{t.__name__}"] = t

    async for node in run:
        if pydantic_ai.Agent.is_user_prompt_node(node):
            yield UserMessageEvent(
                message=node.user_prompt,
            )

        elif pydantic_ai.Agent.is_model_request_node(node):
            # EndTurnTool retries do not get processed as normal
            # FunctionToolResultEvents, but can be detected by checking for
            # RetryPromptPart that match the end turn tool names. Here, we
            # yield a ToolRetryEvent for each RetryPromptPart that matches an
            # end turn tool name.
            for part in node.request.parts:
                if (
                    isinstance(part, RetryPromptPart)
                    and part.tool_name in end_turn_tools_map
                ):
                    yield ToolRetryEvent(message=part)

            # Model request node - stream tokens from the model's request
            async with node.stream(run.ctx) as request_stream:
                async for event in request_stream:
                    try:
                        event = _process_pydantic_event(
                            event=event,
                            actor=actor,
                            parts_manager=parts_manager,
                            tools_map=tools_map,
                            end_turn_tools_map=end_turn_tools_map,
                        )
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

        elif pydantic_ai.Agent.is_call_tools_node(node):
            # Handle-response node - the model returned data, potentially calls a tool
            async with node.stream(run.ctx) as handle_stream:
                async for event in handle_stream:
                    try:
                        event = _process_pydantic_event(
                            event=event,
                            actor=actor,
                            parts_manager=parts_manager,
                            tools_map=tools_map,
                            end_turn_tools_map=end_turn_tools_map,
                        )
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
        elif pydantic_ai.Agent.is_end_node(node):
            tool_call_part = None
            for part in parts_manager.get_parts():
                if (
                    isinstance(part, ToolCallPart)
                    and part.tool_name == node.data.tool_name
                ):
                    tool_call_part = part
                    break
            if tool_call_part is None:
                raise ValueError(
                    f"No tool call part found for {node.data.tool_name}. This is unexpected."
                )

            tool = end_turn_tools_map.get(node.data.tool_name)

            yield EndTurnToolResultEvent(
                actor=actor,
                result=node.data,
                tool_call_id=tool_call_part.tool_call_id,
                tool=tool,
            )
        else:
            logger.warning(f"Unknown node type: {type(node)}")


# Private helper function to process PydanticAI events
def _process_pydantic_event(
    event,
    actor: Actor,
    parts_manager: ModelResponsePartsManager,
    tools_map: dict[str, Callable[..., Any]],
    end_turn_tools_map: dict[str, EndTurn],
) -> Event | None:
    def _get_snapshot(index: int) -> ModelResponsePart:
        return parts_manager.get_parts()[index]

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
                tool=tools_map.get(event.part.tool_name),
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
                tool=tools_map.get(event.delta.tool_name_delta),
            )

    # Handle Function Tool Call Events
    elif isinstance(event, FunctionToolCallEvent):
        # This is the signal that a tool call is complete and ready to be executed
        # Emit tool call complete event
        resolved_tool = tools_map.get(event.part.tool_name)
        return ToolCallEvent(
            actor=actor,
            message=event.part,
            tool_call_id=event.part.tool_call_id,
            tool=resolved_tool,
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
        tool_call_part = None
        for part in parts_manager.get_parts():
            if isinstance(part, ToolCallPart) and part.tool_name == event.tool_name:
                tool_call_part = part
                break
        if tool_call_part is None:
            raise ValueError(
                f"No tool call part found for {event.tool_name}. This is unexpected."
            )

        return EndTurnToolCallEvent(
            actor=actor,
            event=event,
            tool_call_id=tool_call_part.tool_call_id,
            tool=end_turn_tools_map.get(event.tool_name),
        )

    else:
        logger.warning(f"Unknown event type: {type(event)}")
        return None
