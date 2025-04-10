from pathlib import Path

import pytest
from pydantic_ai import BinaryContent, ImageUrl
from pydantic_ai.models.test import TestModel

import marvin
from marvin.engine.events import Event


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
        events: list[Event] = []
        t = marvin.Task("Say 'Hello'")
        async for event in marvin.run_tasks_stream([t]):
            events.append(event)

        assert [e.type for e in events] == [
            "orchestrator-start",
            "actor-start-turn",
            "user-message",
            "tool-call-delta",
            "end-turn-tool-call",
            "end-turn-tool-result",
            "actor-end-turn",
            "orchestrator-end",
        ]

    async def test_run_stream(self, test_model: TestModel):
        events: list[Event] = []
        async for event in marvin.run_stream('Say "Hello"'):
            events.append(event)

        assert [e.type for e in events] == [
            "orchestrator-start",
            "actor-start-turn",
            "user-message",
            "tool-call-delta",
            "end-turn-tool-call",
            "end-turn-tool-result",
            "actor-end-turn",
            "orchestrator-end",
        ]


class TestRunWithAudio:
    @pytest.fixture
    def youre_funny_audio_data(self) -> BinaryContent:
        data = Path(__file__).parent.parent.parent / "data" / "youre-funny.wav"
        return BinaryContent(data=data.read_bytes(), media_type="audio/wav")

    @pytest.mark.usefixtures("gpt_4o_audio_preview")
    def test_run_with_audio(self, youre_funny_audio_data: BinaryContent):
        result = marvin.run(
            [
                "What is this audio saying?",
                youre_funny_audio_data,
            ]
        )
        assert result.lower().startswith("you're funny")
