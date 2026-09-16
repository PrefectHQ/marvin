import json

from pydantic_ai.messages import (
    BinaryContent,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from slackbot.assets import thread_summary_evidence


def test_summary_keeps_roles_and_correction_order():
    messages = [
        ModelRequest(
            parts=[
                SystemPromptPart("internal instructions"),
                UserPromptPart("Why green?"),
            ]
        ),
        ModelResponse(
            parts=[
                TextPart("It was nostalgia."),
                ToolCallPart("lookup", {"query": "green"}, "c1"),
            ]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart("lookup", {"verified": False}, "c1"),
                UserPromptPart("You saw my channel message."),
            ]
        ),
        ModelResponse(parts=[TextPart("My earlier explanation omitted that context.")]),
    ]
    rows = json.loads(thread_summary_evidence(messages))
    assert [row["role"] for row in rows] == [
        "user",
        "assistant",
        "tool",
        "user",
        "assistant",
    ]
    assert rows[2]["result"] == {"verified": False}
    assert rows[-1]["text"] == "My earlier explanation omitted that context."
    assert "internal instructions" not in str(rows)
    assert "query" not in str(rows)


def test_summary_does_not_serialize_attachment_bytes():
    history = [
        ModelRequest(
            parts=[
                UserPromptPart(
                    [
                        "Look at this",
                        BinaryContent(data=b"private pixels", media_type="image/png"),
                    ]
                )
            ]
        )
    ]
    text = thread_summary_evidence(history)
    assert "Look at this" in text
    assert "[attachment omitted]" in text
    assert "private pixels" not in text
