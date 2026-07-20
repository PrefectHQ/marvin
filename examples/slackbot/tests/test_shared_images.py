"""Regression tests for image support in shared Slack messages.

Marvin previously never saw files attached to messages: `SlackEvent`
dropped the `files` array and only `event.text` reached the agent.
"""

import httpx
import pytest
from pydantic_ai import BinaryContent
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from slackbot._internal.message_store import strip_binary_content
from slackbot.slack import (
    MAX_IMAGE_BYTES,
    SlackEvent,
    SlackFile,
    SlackPayload,
    fetch_shared_images,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def make_event_payload(**event_overrides) -> dict:
    event = {
        "type": "app_mention",
        "text": "<@U123BOT> here is a screenshot",
        "user": "U456",
        "ts": "1778543248.702039",
        "channel": "C789",
        "event_ts": "1778543248.702039",
        **event_overrides,
    }
    return {
        "token": "tok",
        "type": "event_callback",
        "team_id": "T1",
        "event": event,
        "authorizations": [
            {
                "team_id": "T1",
                "user_id": "U123BOT",
                "is_bot": True,
                "is_enterprise_install": False,
            }
        ],
    }


class TestSlackFileParsing:
    def test_event_parses_files(self):
        payload = SlackPayload.model_validate(
            make_event_payload(
                files=[
                    {
                        "id": "F123",
                        "name": "image.png",
                        "mimetype": "image/png",
                        "size": 12345,
                        "url_private": "https://files.slack.com/files-pri/T1-F123/image.png",
                    }
                ]
            )
        )
        assert payload.event is not None
        assert payload.event.files is not None
        file = payload.event.files[0]
        assert file.is_image
        assert file.url_private is not None

    def test_event_without_files(self):
        event = SlackEvent.model_validate(make_event_payload()["event"])
        assert event.files is None

    def test_non_image_file_is_not_image(self):
        file = SlackFile(id="F1", mimetype="application/pdf")
        assert not file.is_image

    def test_extract_message_context_returns_files(self):
        from slackbot.api import _extract_message_context

        event = SlackEvent.model_validate(
            make_event_payload(
                files=[
                    {"id": "F1", "mimetype": "image/png", "url_private": "https://x"}
                ]
            )["event"]
        )
        is_edit, message_ts, thread_ts, text, files = _extract_message_context(event)
        assert not is_edit
        assert len(files) == 1
        assert files[0].id == "F1"

    def test_extract_message_context_edit_event_files(self):
        from slackbot.api import _extract_message_context

        event = SlackEvent.model_validate(
            {
                "type": "message",
                "subtype": "message_changed",
                "channel": "C789",
                "event_ts": "1778543249.000000",
                "message": {
                    "ts": "1778543248.702039",
                    "text": "<@U123BOT> edited",
                    "files": [
                        {
                            "id": "F2",
                            "mimetype": "image/jpeg",
                            "url_private": "https://y",
                        }
                    ],
                },
            }
        )
        is_edit, message_ts, thread_ts, text, files = _extract_message_context(event)
        assert is_edit
        assert len(files) == 1
        assert files[0].id == "F2"


def _mock_transport(content: bytes, content_type: str = "image/png"):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"].startswith("Bearer ")
        return httpx.Response(
            200, content=content, headers={"content-type": content_type}
        )

    return httpx.MockTransport(handler)


class TestFetchSharedImages:
    @pytest.fixture(autouse=True)
    def patch_httpx(self, monkeypatch: pytest.MonkeyPatch):
        self.transport = _mock_transport(PNG_BYTES)
        original_init = httpx.AsyncClient.__init__

        def patched_init(client, **kwargs):
            kwargs["transport"] = self.transport
            original_init(client, **kwargs)

        monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)

    async def test_downloads_image_as_binary_content(self):
        files = [
            SlackFile(
                id="F1",
                name="image.png",
                mimetype="image/png",
                url_private="https://files.slack.com/x",
            )
        ]
        images = await fetch_shared_images(files)
        assert len(images) == 1
        assert isinstance(images[0], BinaryContent)
        assert images[0].data == PNG_BYTES
        assert images[0].media_type == "image/png"

    async def test_skips_non_image_files(self):
        files = [SlackFile(id="F1", mimetype="text/plain", url_private="https://x")]
        assert await fetch_shared_images(files) == []

    async def test_skips_files_without_url(self):
        files = [SlackFile(id="F1", mimetype="image/png")]
        assert await fetch_shared_images(files) == []

    async def test_skips_oversized_images(self):
        files = [
            SlackFile(
                id="F1",
                mimetype="image/png",
                size=MAX_IMAGE_BYTES + 1,
                url_private="https://x",
            )
        ]
        assert await fetch_shared_images(files) == []

    async def test_caps_image_count(self):
        files = [
            SlackFile(id=f"F{i}", mimetype="image/png", url_private="https://x")
            for i in range(10)
        ]
        images = await fetch_shared_images(files)
        assert len(images) == 4

    async def test_skips_non_image_response(self):
        # e.g. HTML login page when token lacks files:read scope
        self.transport = _mock_transport(
            b"<html>login</html>", content_type="text/html"
        )
        files = [SlackFile(id="F1", mimetype="image/png", url_private="https://x")]
        assert await fetch_shared_images(files) == []

    async def test_download_failure_does_not_raise(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403)

        self.transport = httpx.MockTransport(handler)
        files = [SlackFile(id="F1", mimetype="image/png", url_private="https://x")]
        assert await fetch_shared_images(files) == []


class TestStripBinaryContent:
    def test_replaces_binary_with_placeholder(self):
        messages = [
            ModelRequest(
                parts=[
                    UserPromptPart(
                        content=[
                            "look at this",
                            BinaryContent(
                                data=PNG_BYTES,
                                media_type="image/png",
                                identifier="image.png",
                            ),
                        ]
                    )
                ]
            ),
            ModelResponse(parts=[TextPart(content="I see a pod crashlooping")]),
        ]
        stripped = strip_binary_content(messages)
        request = stripped[0]
        assert isinstance(request, ModelRequest)
        part = request.parts[0]
        assert isinstance(part, UserPromptPart)
        assert part.content[0] == "look at this"
        assert isinstance(part.content[1], str)
        assert "image.png" in part.content[1]

    def test_plain_text_messages_unchanged(self):
        messages = [
            ModelRequest(parts=[UserPromptPart(content="hi")]),
            ModelResponse(parts=[TextPart(content="hello")]),
        ]
        assert strip_binary_content(messages) == messages

    def test_originals_not_mutated(self):
        binary = BinaryContent(data=PNG_BYTES, media_type="image/png")
        messages = [ModelRequest(parts=[UserPromptPart(content=["hi", binary])])]
        strip_binary_content(messages)
        assert messages[0].parts[0].content[1] is binary
