from tests.utils.mark import pytest_mark_class


class TestRegressions:
    def test_key_1(self):
        from marvin import openai

        openai.api_key = "test"
        v = openai.ChatCompletion.prepare_request()._config.api_key.get_secret_value()
        assert v == "test"

    def test_key_2(self):
        import os

        from marvin import openai

        os.environ["OPENAI_API_KEY"] = "test"
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
