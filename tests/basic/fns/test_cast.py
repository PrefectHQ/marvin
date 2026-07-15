from __future__ import annotations

from typing import Any

import pytest
from pydantic_ai import (
    AudioUrl,
    BinaryContent,
    BinaryImage,
    DocumentUrl,
    ImageUrl,
    VideoUrl,
)

import marvin
from marvin.fns.cast import cast_async


class _TaskCapture:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = self.calls

        class FakeTask:
            @classmethod
            def __class_getitem__(cls, item: Any) -> type[FakeTask]:
                return cls

            def __init__(self, **kwargs: Any) -> None:
                calls.append(kwargs)

            async def run_async(self, **kwargs: Any) -> str:
                return "accepted"

        monkeypatch.setattr(marvin, "Task", FakeTask)


@pytest.mark.parametrize(
    "data",
    [
        BinaryImage(data=b"image", media_type="image/png"),
        BinaryContent(data=b"audio", media_type="audio/mpeg"),
        ImageUrl(url="https://example.com/image.png"),
        AudioUrl(url="https://example.com/audio.mp3"),
        DocumentUrl(url="https://example.com/document.pdf"),
        VideoUrl(url="https://example.com/video.mp4"),
    ],
)
async def test_cast_routes_user_content_to_attachments(
    monkeypatch: pytest.MonkeyPatch,
    data: Any,
) -> None:
    capture = _TaskCapture()
    capture.install(monkeypatch)
    context = {"caller": "preserved"}

    result = await cast_async(
        data,
        target=str,
        instructions="Describe the attachment",
        context=context,
    )

    assert result == "accepted"
    assert len(capture.calls) == 1
    assert capture.calls[0]["attachments"] == [data]
    assert capture.calls[0]["attachments"][0] is data
    assert "Data to transform" not in capture.calls[0]["context"]
    assert context == {"caller": "preserved"}


class _BinaryLookalike:
    data = b"not-user-content"
    media_type = "image/png"


@pytest.mark.parametrize(
    "data",
    [
        "plain text",
        {"key": "value"},
        b"raw bytes",
        bytearray(b"raw bytearray"),
        _BinaryLookalike(),
    ],
)
async def test_cast_keeps_other_values_in_context(
    monkeypatch: pytest.MonkeyPatch,
    data: Any,
) -> None:
    capture = _TaskCapture()
    capture.install(monkeypatch)

    result = await cast_async(
        data,
        target=str,
        instructions="Transform the value",
    )

    assert result == "accepted"
    assert len(capture.calls) == 1
    assert capture.calls[0]["attachments"] == []
    assert capture.calls[0]["context"]["Data to transform"] is data
