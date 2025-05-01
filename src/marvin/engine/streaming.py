from collections.abc import Callable
from typing import Any, Literal

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
    UserPromptPart,
)
from pydantic_ai.result import DEFAULT_OUTPUT_TOOL_NAME

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

    # --- Tool Mapping Setup --- #
    # Map Marvin-defined tools
    marvin_tools_map = {t.__name__: t for t in agentlet._marvin_tools}

    # Map Marvin-defined EndTurn tools
    end_turn_tools_map = {}
    for t in agentlet._marvin_end_turn_tools:
        tool_name = getattr(t, "__name__", str(t))  # Handle instances vs types
        end_turn_tools_map[tool_name] = t
        # Also map deprecated name format if applicable
        if agentlet._deprecated_result_tool_name:
            end_turn_tools_map[
                f"{agentlet._deprecated_result_tool_name}_{tool_name}"
            ] = t

    # Attempt to access discovered MCP tools from Pydantic AI agent internals
    # NOTE: Accessing internal attribute `_mcp_tools_by_server` - might break
    mcp_tools_map: dict[str, Any] = {}
    if hasattr(agentlet, "_mcp_tools_by_server") and agentlet._mcp_tools_by_server:
        logger.debug("Found MCP tools registered within Pydantic AI agent.")
        # We might just need the names, or potentially the ToolDefinition objects
        # For now, let's just store the names to identify them.
        # The value could be the ToolDefinition if needed later.
        mcp_tools_map = {
            name: "mcp_tool" for name in agentlet._mcp_tools_by_server.keys()
        }
    elif hasattr(agentlet, "_mcp_servers") and agentlet._mcp_servers:
        # Fallback if _mcp_tools_by_server isn't populated/available?
        # This case seems less likely based on pydantic-ai code.
        logger.warning(
            "Pydantic AI agent has MCP servers but no discovered tools map (`_mcp_tools_by_server`). MCP tool events might not be handled correctly."
        )

    # Combine maps for easier lookup? Or check sequentially?
    # Let's pass maps separately for clarity in _process_pydantic_event
    # --- End Tool Mapping Setup --- #

    async for node in run:
        if pydantic_ai.Agent.is_user_prompt_node(node):
            # Construct UserPromptPart, handling potential sequence
            prompt_content = node.user_prompt
            if not isinstance(prompt_content, str):
                # Basic handling: join content if it's a sequence
                # More sophisticated handling might be needed depending on UserContent structure
                prompt_content = " ".join(str(item) for item in (prompt_content or []))

            user_prompt_part = UserPromptPart(content=prompt_content)
            yield UserMessageEvent(
                message=user_prompt_part,
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
                            # Pass tool maps
                            marvin_tools_map=marvin_tools_map,
                            mcp_tools_map=mcp_tools_map,
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
                            # Pass tool maps
                            marvin_tools_map=marvin_tools_map,
                            mcp_tools_map=mcp_tools_map,
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
            logger.debug(
                f"[_handle_agentlet_events] Processing End node. node.data: {node.data!r}"
            )
            end_node_tool_name = getattr(node.data, "tool_name", None)

            # --- Handle final text output case --- >
            if end_node_tool_name == DEFAULT_OUTPUT_TOOL_NAME:
                logger.debug(
                    f"[_handle_agentlet_events] End node is for final text output ('{DEFAULT_OUTPUT_TOOL_NAME}'). Ending event stream."
                )
                # Final text message should have been streamed via deltas processed by _process_pydantic_event.
                # Break the loop to signal the end of this agent run.
                break
            # <-------------------------------------

            # --- Handle EndTurn tool case --- >
            logger.debug(
                f"[_handle_agentlet_events] End node is assumed to be for an EndTurn tool: '{end_node_tool_name}'."
            )
            tool_call_part = None
            # Look for the corresponding tool call part to get the ID
            for part in parts_manager.get_parts():
                if (
                    isinstance(part, ToolCallPart)
                    and part.tool_name == end_node_tool_name
                ):
                    tool_call_part = part
                    logger.debug(
                        f"[_handle_agentlet_events] Found matching ToolCallPart: {part.tool_call_id}"
                    )
                    break

            if tool_call_part is None:
                # This might happen if the EndTurn tool didn't have a preceding ToolCallPart (e.g., direct return?)
                # Or if the final_result case wasn't handled correctly above.
                # Log a warning instead of raising an error for now.
                logger.warning(
                    f"[_handle_agentlet_events] No tool call part found for End node tool '{end_node_tool_name}'. Cannot create EndTurnToolResultEvent without tool_call_id."
                )
                # Optionally, break here too if this state is unrecoverable?
                # break
                continue  # Skip yielding the event if ID is missing

            tool = end_turn_tools_map.get(end_node_tool_name)
            if not tool:
                logger.warning(
                    f"[_handle_agentlet_events] Could not map end node tool '{end_node_tool_name}' to a known EndTurn tool."
                )
                # If tool is None or not an EndTurn instance, we probably shouldn't yield the event.
                # However, the original code yielded with tool=None. Let's keep that but log.
                pass  # Explicitly do nothing if mapping failed, yield below handles None tool

            # Add type check before yielding
            if tool is not None and not isinstance(tool, EndTurn):
                logger.error(
                    f"[_handle_agentlet_events] Mapped tool '{end_node_tool_name}' is not an EndTurn instance: {type(tool)}"
                )
                # What should happen here? Skip yielding? Yield with tool=None?
                # For now, let's proceed but the event might be incorrect.

            yield EndTurnToolResultEvent(
                actor=actor,
                result=node.data,  # Contains the EndTurn object
                tool_call_id=tool_call_part.tool_call_id,
                tool=tool,  # The mapped EndTurn tool (or None)
            )
            # <-----------------------------
        else:
            logger.warning(f"Unknown node type: {type(node)}")


# Private helper function to process PydanticAI events
def _process_pydantic_event(
    event: Any,
    actor: Actor,
    parts_manager: ModelResponsePartsManager,
    marvin_tools_map: dict[str, Callable[..., Any]],
    mcp_tools_map: dict[str, Any],
    end_turn_tools_map: dict[str, EndTurn],
) -> Event | None:
    """Processes a single event from Pydantic AI and yields a Marvin event."""
    logger.debug(
        f"[_process_pydantic_event] Received Pydantic AI event: {type(event).__name__}, {event!r}"
    )

    # --- Handle FinalResultEvent first and return --- >
    if isinstance(event, FinalResultEvent):
        logger.debug(
            "[_process_pydantic_event] Received FinalResultEvent. No Marvin event yielded."
        )
        return None
    # <--------------------------------------------------

    def _get_snapshot(index: int) -> ModelResponsePart:
        return parts_manager.get_parts()[index]

    marvin_event: Event | None = None

    try:
        tool: Callable[..., Any] | EndTurn | None = None
        tool_source: Literal["marvin", "mcp", "endturn"] | None = None
        tool_name = None

        # Extract tool name from relevant events (excluding FinalResultEvent now)
        if isinstance(event, PartStartEvent) and event.part.part_kind == "tool-call":
            tool_name = event.part.tool_name
            logger.debug(
                f"[_process_pydantic_event] Extracted tool_name '{tool_name}' from PartStartEvent"
            )
        elif isinstance(event, PartDeltaEvent) and isinstance(
            event.delta, ToolCallPartDelta
        ):
            if event.delta.tool_name_delta is not None:
                tool_name = event.delta.tool_name_delta
                logger.debug(
                    f"[_process_pydantic_event] Extracted tool_name '{tool_name}' from ToolCallPartDelta"
                )
            else:
                try:
                    snapshot = _get_snapshot(event.index)
                    if isinstance(snapshot, ToolCallPart):
                        tool_name = snapshot.tool_name
                        logger.debug(
                            f"[_process_pydantic_event] Got tool_name '{tool_name}' from snapshot for ToolCallPartDelta"
                        )
                except IndexError:
                    logger.warning(
                        f"Could not find snapshot for PartDeltaEvent at index {event.index}"
                    )
        elif isinstance(event, FunctionToolCallEvent):
            tool_name = event.tool_name
            logger.debug(
                f"[_process_pydantic_event] Extracted tool_name '{tool_name}' from FunctionToolCallEvent"
            )
        elif isinstance(event, FunctionToolResultEvent):
            tool_name = event.tool_name
            logger.debug(
                f"[_process_pydantic_event] Extracted tool_name '{tool_name}' from FunctionToolResultEvent"
            )

        # Map tool name to tool object and source
        if tool_name:
            # --- Skip mapping for default final output --- >
            if tool_name == DEFAULT_OUTPUT_TOOL_NAME:
                logger.debug(
                    "[_process_pydantic_event] Tool name is default output, skipping mapping."
                )
            # <-------------------------------------------
            else:
                logger.debug(
                    f"[_process_pydantic_event] Mapping tool_name '{tool_name}'"
                )
                if tool_name in marvin_tools_map:
                    tool = marvin_tools_map[tool_name]
                    tool_source = "marvin"
                    logger.debug(
                        f"[_process_pydantic_event] Mapped to marvin tool: {tool!r}"
                    )
                elif tool_name in mcp_tools_map:
                    tool = None  # Placeholder
                    tool_source = "mcp"
                    logger.debug("[_process_pydantic_event] Mapped to mcp tool.")
                elif tool_name in end_turn_tools_map:
                    tool = end_turn_tools_map[tool_name]
                    tool_source = "endturn"
                    logger.debug(
                        f"[_process_pydantic_event] Mapped to endturn tool: {tool!r}"
                    )
                else:
                    logger.warning(
                        f"[_process_pydantic_event] Could not map tool_name '{tool_name}' to any known source."
                    )

        # Handle Part Start Events
        if isinstance(event, PartStartEvent):
            if event.part.part_kind == "text":
                parts_manager.handle_text_delta(
                    vendor_part_id=event.index, content=event.part.content
                )
                # No Marvin event yielded here, handled by delta
            elif event.part.part_kind == "tool-call":
                # This event marks the *start* of the tool call part, often before args are known
                # We rely on deltas to fill in details. We *don't* yield ToolCallEvent here.
                parts_manager.handle_tool_call_delta(
                    vendor_part_id=event.index,
                    tool_call_id=event.part.tool_call_id,
                    tool_name=event.part.tool_name,
                    args=event.part.args,
                )
                logger.debug(
                    f"[_process_pydantic_event] Handling PartStartEvent for tool call {event.part.tool_name} (ID: {event.part.tool_call_id}). Manager updated."
                )

        # Handle Part Delta Events
        elif isinstance(event, PartDeltaEvent):
            snapshot_idx = event.index
            if isinstance(event.delta, TextPartDelta):
                parts_manager.handle_text_delta(
                    vendor_part_id=snapshot_idx, content=event.delta.content_delta
                )
                snapshot = _get_snapshot(snapshot_idx)
                marvin_event = ActorMessageDeltaEvent(actor=actor, snapshot=snapshot)
            elif isinstance(event.delta, ToolCallPartDelta):
                parts_manager.handle_tool_call_delta(
                    vendor_part_id=snapshot_idx,
                    tool_call_id=event.delta.tool_call_id,
                    tool_name=event.delta.tool_name_delta,
                    args=event.delta.args_delta,
                )
                snapshot = _get_snapshot(snapshot_idx)
                marvin_event = ToolCallDeltaEvent(
                    actor=actor,
                    delta=event.delta,
                    snapshot=snapshot,
                    tool_call_id=snapshot.tool_call_id,
                    tool=tool,
                )

        # Handle Function Tool Call Events (produced by Call Tools node)
        elif isinstance(event, FunctionToolCallEvent):
            logger.debug(
                f"[_process_pydantic_event] Processing FunctionToolCallEvent for tool '{event.tool_name}'"
            )
            # Find the corresponding ToolCallPart using the tool_call_id
            tool_call_part = parts_manager.get_tool_call_by_id(event.tool_call_id)
            if tool_call_part:
                if tool_source == "endturn":
                    marvin_event = EndTurnToolCallEvent(
                        actor=actor, tool_call=tool_call_part, tool=tool
                    )
                else:
                    marvin_event = ToolCallEvent(
                        actor=actor, tool_call=tool_call_part, tool_source=tool_source
                    )
            else:
                logger.error(
                    f"Could not find ToolCallPart for FunctionToolCallEvent ID: {event.tool_call_id}"
                )

        # Handle Function Tool Result Events (produced by Call Tools node)
        elif isinstance(event, FunctionToolResultEvent):
            logger.debug(
                f"[_process_pydantic_event] Processing FunctionToolResultEvent for tool '{event.tool_name}'"
            )
            # Find the corresponding ToolCallPart using the tool_call_id
            tool_call_part = parts_manager.get_tool_call_by_id(event.tool_call_id)
            if tool_call_part:
                # We don't yield EndTurnToolResultEvent here, it's handled by the End node
                if tool_source != "endturn":
                    marvin_event = ToolResultEvent(
                        actor=actor,
                        tool_call=tool_call_part,
                        tool_result=event,
                        tool_source=tool_source,
                    )
            else:
                logger.error(
                    f"Could not find ToolCallPart for FunctionToolResultEvent ID: {event.tool_call_id}"
                )

        else:
            logger.warning(
                f"[_process_pydantic_event] Unhandled Pydantic AI event type: {type(event).__name__}"
            )

    except Exception as e:
        logger.error(
            f"[_process_pydantic_event] Error during processing: {e}", exc_info=True
        )
        marvin_event = None  # Ensure we don't yield a partial/broken event

    if marvin_event:
        logger.debug(
            f"[_process_pydantic_event] Yielding Marvin event: {type(marvin_event).__name__}"
        )
    return marvin_event
