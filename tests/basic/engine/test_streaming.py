import inspect

import pydantic_ai.messages as messages
import pytest
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


@pytest.mark.skipif(
    not hasattr(messages, "OutputToolResultEvent"),
    reason="requires current tool outcome events",
)
@pytest.mark.parametrize(
    "event_name", ["FunctionToolResultEvent", "OutputToolResultEvent"]
)
@pytest.mark.parametrize("outcome", ["success", "retried"])
def test_current_tool_result_events(event_name, outcome):
    from marvin.engine.events import ToolResultEvent, ToolRetryEvent

    part = messages.ToolReturnPart(
        tool_name="lookup",
        content="try again" if outcome == "retried" else "42",
        tool_call_id="call-1",
        outcome=outcome,
    )
    event = getattr(messages, event_name)(part=part)
    result = _process_pydantic_event(event, Agent(), {}, {}, {})
    if outcome == "retried":
        assert isinstance(result, ToolRetryEvent)
        assert result.message is part
    elif event_name == "OutputToolResultEvent":
        assert result is None
    else:
        assert isinstance(result, ToolResultEvent)
        assert result.message is part


def test_legacy_retry_event():
    from marvin.engine.events import ToolRetryEvent

    part = messages.RetryPromptPart(
        tool_name="lookup", content="try again", tool_call_id="call-1"
    )
    parameter = (
        "part"
        if "part" in inspect.signature(messages.FunctionToolResultEvent).parameters
        else "result"
    )
    event = messages.FunctionToolResultEvent(**{parameter: part})
    result = _process_pydantic_event(event, Agent(), {}, {}, {})
    assert isinstance(result, ToolRetryEvent)
    assert result.message is part
