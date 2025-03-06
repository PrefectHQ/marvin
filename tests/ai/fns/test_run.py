from pydantic_ai import ImageUrl
from pydantic_ai.models.test import TestModel

import marvin


class TestRun:
    def test_run(self):
        result = marvin.run('Say "Hello"')
        assert result == "Hello"


class TestRunWithAttachments:
    def test_run_with_attachments(self):
        result = marvin.run(
            "What company's logo is this?",
            attachments=[
                ImageUrl(
                    "https://1000logos.net/wp-content/uploads/2021/05/Coca-Cola-logo.png"
                )
            ],
        )
        assert "Coca-Cola" in result

    def test_run_with_attachments_as_list(self):
        result = marvin.run(
            [
                "What company's logo is this?",
                ImageUrl(
                    "https://1000logos.net/wp-content/uploads/2021/05/Coca-Cola-logo.png"
                ),
            ],
        )
        assert "Coca-Cola" in result


class TestRunStream:
    async def test_run_tasks_stream(self, test_model: TestModel):
        events = []
        t = marvin.Task("Say 'Hello'")
        async for event in marvin.run_tasks_stream([t]):
            events.append(event)

        assert [e.type for e in events] == [
            "orchestrator-start",
            "actor-start-turn",
            "tool-call-delta",
            "end-turn-tool-call",
            "end-turn-tool-result",
            "actor-end-turn",
            "orchestrator-end",
        ]

    async def test_run_stream(self, test_model: TestModel):
        events = []
        async for event in marvin.run_stream('Say "Hello"'):
            events.append(event)

        assert [e.type for e in events] == [
            "orchestrator-start",
            "actor-start-turn",
            "tool-call-delta",
            "end-turn-tool-call",
            "end-turn-tool-result",
            "actor-end-turn",
            "orchestrator-end",
        ]
