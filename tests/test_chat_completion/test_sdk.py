from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from marvin import openai
from marvin.core.ChatCompletion.abstract import Conversation

from tests.utils.mark import pytest_mark_class


@pytest.fixture
def mock_completion():
    return {
        "id": "chatcmpl-8BdS5cSTx1oqGvIa0U5dXf4pNpVVN",
        "object": "chat.completion",
        "created": 1697783953,
        "model": "gpt-3.5-turbo-0613",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I assist you today?",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 8, "completion_tokens": 9, "total_tokens": 17},
    }


@pytest.fixture
def mock_create_methods(mock_completion):
    with (
        patch(
            "openai.ChatCompletion.create", MagicMock(return_value=mock_completion)
        ) as mock_create,
        patch(
            "openai.ChatCompletion.acreate", AsyncMock(return_value=mock_completion)
        ) as mock_acreate,
    ):
        yield mock_create, mock_acreate


class TestOriginalOpenAICompatibility:
    async def test_create_class_methods(self, mock_create_methods, mock_completion):
        """in OpenAIs SDK, `create` and `acreate` are class methods"""

        response = openai.ChatCompletion.create(
            messages=[{"role": "user", "content": "Hello"}],
        )

        other_response = await openai.ChatCompletion.acreate(
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert response == other_response == mock_completion

        for mock_method in mock_create_methods:
            mock_method.assert_called_once()
            _, kwargs = mock_method.call_args

            assert kwargs["messages"] == [{"role": "user", "content": "Hello"}]
            assert "max_tokens" in kwargs
            assert "api_key" in kwargs
            assert "temperature" in kwargs
            assert "request_timeout" in kwargs


class TestRegressions:
    def test_key_set_via_attr(self, monkeypatch):
        from marvin import openai

        monkeypatch.setattr(openai, "api_key", "test")
        v = openai.ChatCompletion().defaults.get("api_key")
        assert v == "test"

    @pytest.mark.parametrize("valid_env_var", ["MARVIN_OPENAI_API_KEY"])
    def test_key_set_via_env(self, monkeypatch, valid_env_var):
        monkeypatch.setenv(valid_env_var, "test")
        from marvin import openai

        v = openai.ChatCompletion().defaults.get("api_key")
        assert v == "test"

    def facet(self):
        messages = [{"role": "user", "content": "hey"}]
        from marvin import openai

        faceted = openai.ChatCompletion(messages=messages)
        faceted_request = faceted.prepare_request(messages=messages)
        assert faceted_request.messages == 2 * messages


@pytest_mark_class("llm")
class TestChatCompletion:
    def test_response_model(self):
        import pydantic
        from marvin import openai

        class Person(pydantic.BaseModel):
            name: str
            age: int

        response = openai.ChatCompletion().create(
            messages=[{"role": "user", "content": "Billy is 10 years old"}],
            response_model=Person,
        )

        model = response.to_model()
        assert model.name == "Billy"
        assert model.age == 10


@pytest_mark_class("llm")
class TestChatCompletionChain:
    def test_chain(self):
        convo = openai.ChatCompletion().chain(
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert isinstance(convo, Conversation)
        assert len(convo.turns) == 1

    async def test_achain(self):
        convo = await openai.ChatCompletion().achain(
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert isinstance(convo, Conversation)
        assert len(convo.turns) == 1
