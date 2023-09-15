import pytest
from marvin.core.ChatCompletion.base import BaseConversationState

from tests.utils.mark import pytest_mark_class


class TestRegressions:
    def test_key_set_via_attr(self, monkeypatch):
        from marvin import openai

        monkeypatch.setattr(openai, "api_key", "test")
        v = openai.ChatCompletion.prepare_request()._config.api_key.get_secret_value()
        assert v == "test"

    @pytest.mark.parametrize("valid_env_var", ["MARVIN_OPENAI_API_KEY"])
    def test_key_set_via_env(self, monkeypatch, valid_env_var):
        monkeypatch.setenv(valid_env_var, "test")
        from marvin import openai

        v = openai.ChatCompletion.prepare_request()._config.api_key.get_secret_value()
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

        response = openai.ChatCompletion.create(
            messages=[{"role": "user", "content": "Billy is 10 years old"}],
            response_model=Person,
        )

        model = response.to_model()
        assert model.name == "Billy"
        assert model.age == 10


@pytest_mark_class("llm")
class TestChatCompletionChain:
    def test_chain(self):
        from marvin import openai

        convo = openai.ChatCompletion().chain(
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert isinstance(convo, BaseConversationState)
        assert len(convo.turns) == 1

    async def test_achain(self):
        from marvin import openai

        convo = await openai.ChatCompletion().achain(
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert isinstance(convo, BaseConversationState)
        assert len(convo.turns) == 1
