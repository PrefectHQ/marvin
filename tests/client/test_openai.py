import marvin
import pytest
from marvin.client.openai import AsyncMarvinClient, MarvinClient
from marvin.settings import temporary_settings
from marvin.types import BaseMessage, StreamingChatResponse
from openai.types.chat import ChatCompletion


class TestStreaming:
    def test_chat(self):
        buffer = []
        client = MarvinClient()
        response = client.generate_chat(
            messages=[BaseMessage(role="user", content="Hello!")],
            stream=True,
            stream_callback=lambda response: buffer.append(response),
        )
        assert isinstance(response, ChatCompletion)
        assert len(buffer) > 1
        assert all(isinstance(c, StreamingChatResponse) for c in buffer)
        assert buffer[-1].completion is response

    def test_providing_callback_turns_on_streaming(self):
        buffer = []
        client = MarvinClient()
        response = client.generate_chat(
            messages=[BaseMessage(role="user", content="Hello!")],
            stream_callback=lambda response: buffer.append(response),
        )
        assert isinstance(response, ChatCompletion)
        assert len(buffer) > 1

    def test_can_turn_off_streaming_even_if_callback_provided(self):
        buffer = []
        client = MarvinClient()
        response = client.generate_chat(
            messages=[BaseMessage(role="user", content="Hello!")],
            stream=False,
            stream_callback=lambda response: buffer.append(response),
        )
        assert isinstance(response, ChatCompletion)
        assert len(buffer) == 0


class TestStreamingAsync:
    async def test_chat(self):
        buffer = []
        client = AsyncMarvinClient()
        response = await client.generate_chat(
            messages=[BaseMessage(role="user", content="Hello!")],
            stream=True,
            stream_callback=lambda response: buffer.append(response),
        )
        assert isinstance(response, ChatCompletion)
        assert len(buffer) > 1
        assert all(isinstance(c, StreamingChatResponse) for c in buffer)
        assert buffer[-1].completion is response

    async def test_providing_callback_turns_on_streaming(self):
        buffer = []
        client = AsyncMarvinClient()
        response = await client.generate_chat(
            messages=[BaseMessage(role="user", content="Hello!")],
            stream_callback=lambda response: buffer.append(response),
        )
        assert isinstance(response, ChatCompletion)
        assert len(buffer) > 1

    async def test_can_turn_off_streaming_even_if_callback_provided(self):
        buffer = []
        client = AsyncMarvinClient()
        response = await client.generate_chat(
            messages=[BaseMessage(role="user", content="Hello!")],
            stream=False,
            stream_callback=lambda response: buffer.append(response),
        )
        assert isinstance(response, ChatCompletion)
        assert len(buffer) == 0


class TempTestClient(AsyncMarvinClient):
    def generate_chat(self, *args, **kwargs):
        raise NotImplementedError()


class TestChangeClient:
    def test_change_client_class(self):
        with temporary_settings(default_async_client_cls=TempTestClient):
            with pytest.raises(NotImplementedError):
                marvin.classify("book", ["thing you read", "thing you sing"])

    def test_change_client_path(self):
        with temporary_settings(
            default_async_client_cls="tests.client.test_openai.TempTestClient"
        ):
            with pytest.raises(NotImplementedError):
                marvin.classify("book", ["thing you read", "thing you sing"])
