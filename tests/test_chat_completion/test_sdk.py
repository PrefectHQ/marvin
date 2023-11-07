import pytest
from marvin._compat import OPENAI_V1
from marvin.core.ChatCompletion.abstract import Conversation

from tests.utils.mark import pytest_mark_class

pytestmark = pytest.mark.skipif(
    OPENAI_V1, reason="This test suite is for v0.x openai sdk only"
)


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

    def test_streaming(self):
        from marvin import openai

        streamed_data = []

        def handler(message):
            streamed_data.append(message.content)

        completion = openai.ChatCompletion(stream_handler=handler).create(
            messages=[{"role": "user", "content": "say only 'hello'"}],
        )

        assert completion.response.choices[0].message.content == streamed_data[-1]
        assert "hello" in streamed_data[-1].lower()
        assert len(streamed_data) > 1

    async def test_streaming_async(self):
        from marvin import openai

        streamed_data = []

        async def handler(message):
            streamed_data.append(message.content)

        completion = await openai.ChatCompletion(stream_handler=handler).acreate(
            messages=[{"role": "user", "content": "say only 'hello'"}],
        )
        assert completion.response.choices[0].message.content == streamed_data[-1]
        assert "hello" in streamed_data[-1].lower()
        assert len(streamed_data) > 1


@pytest_mark_class("llm")
class TestChatCompletionChain:
    def test_chain(self):
        from marvin import openai

        convo = openai.ChatCompletion().chain(
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert isinstance(convo, Conversation)
        assert len(convo.turns) == 1

    async def test_achain(self):
        from marvin import openai

        convo = await openai.ChatCompletion().achain(
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert isinstance(convo, Conversation)
        assert len(convo.turns) == 1
