"""Tests for the streaming module."""

from pydantic_ai._parts_manager import ModelResponsePartsManager
from pydantic_ai.messages import PartDeltaEvent, ToolCallPartDelta

from marvin import Agent
from marvin.engine.streaming import _process_pydantic_event


def test_get_snapshot_with_incomplete_tool_call():
    """Test that _get_snapshot handles ToolCallPartDelta correctly.

    This tests the fix for issue #1207 where accessing get_parts()[index]
    would raise IndexError when the part at that index is a ToolCallPartDelta
    that gets filtered out by get_parts().
    """
    # Setup
    parts_manager = ModelResponsePartsManager()
    actor = Agent(name="test")
    tools_map = {}
    end_turn_tools_map = {}

    # Create an incomplete tool call (ToolCallPartDelta with no tool name)
    # This simulates what happens when streaming starts a tool call
    parts_manager.handle_tool_call_delta(
        vendor_part_id=0,
        tool_name=None,  # No tool name yet - creates ToolCallPartDelta
        args="",
        tool_call_id=None,
    )

    # Verify the setup - we should have a ToolCallPartDelta in _parts
    # but get_parts() should return empty
    assert len(parts_manager._parts) == 1
    assert len(parts_manager.get_parts()) == 0

    # Create a PartDeltaEvent that references index 0
    event = PartDeltaEvent(index=0, delta=ToolCallPartDelta(args_delta="{"))

    # Process the event - this should NOT raise IndexError
    # Before the fix, this would fail with "list index out of range"
    result = _process_pydantic_event(
        event=event,
        actor=actor,
        parts_manager=parts_manager,
        tools_map=tools_map,
        end_turn_tools_map=end_turn_tools_map,
    )

    # The result should be a ToolCallDeltaEvent with the snapshot
    assert result is not None
    assert hasattr(result, "snapshot")
    # The snapshot should be the ToolCallPartDelta from _parts[0]
    assert result.snapshot == parts_manager._parts[0]
