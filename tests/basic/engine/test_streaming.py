from pydantic_ai.messages import (
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
)

from marvin import Agent
from marvin.engine.streaming import _process_pydantic_event


def test_incomplete_tool_call_snapshot():
    parts = {0: ToolCallPartDelta(args_delta="", tool_call_id="call-1")}
    event = PartDeltaEvent(index=0, delta=ToolCallPartDelta(args_delta="{"))
    result = _process_pydantic_event(event, Agent(), parts, {}, {})
    assert result.snapshot.args_delta == "{"
    assert result.tool_call_id == "call-1"


def test_interleaved_streaming_parts():
    actor = Agent()
    parts = {}
    events = [
        PartStartEvent(index=0, part=TextPart(content="Checking ")),
        PartStartEvent(
            index=1,
            part=ToolCallPart(
                tool_name="lookup", args='{"city":', tool_call_id="call-1"
            ),
        ),
        PartDeltaEvent(index=0, delta=TextPartDelta(content_delta="weather")),
        PartDeltaEvent(index=1, delta=ToolCallPartDelta(args_delta='"Chicago"}')),
    ]
    results = [_process_pydantic_event(event, actor, parts, {}, {}) for event in events]
    assert results[0].snapshot.content == "Checking "
    assert results[2].snapshot.content == "Checking weather"
    assert results[3].snapshot.args_as_dict() == {"city": "Chicago"}
    assert results[3].tool_call_id == "call-1"
