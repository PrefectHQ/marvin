<<<<<<< HEAD
from pydantic_ai import ImageUrl
from pydantic_ai.models.test import TestModel
=======
from pathlib import Path

import pytest
from pydantic_ai import BinaryContent, ImageUrl
>>>>>>> d450e4b0 (move to simpler bytes ser)

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
class TestRunWithAudio:
    @pytest.fixture
    def youre_funny_audio_data(self) -> BinaryContent:
        data = Path(__file__).parent.parent.parent / "data" / "youre-funny-2.wav"
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
