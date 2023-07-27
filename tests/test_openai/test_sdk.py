from tests.utils.mark import pytest_mark_class


class TestRegressions:
    def test_imports(self):
        from marvin import openai
        from marvin.openai import ChatCompletion as ChatCompletion1
        from marvin.openai.ChatCompletion import ChatCompletion as ChatCompletion2

        assert openai.ChatCompletion == ChatCompletion1
        assert openai.ChatCompletion == ChatCompletion2

    def test_default_settings(self):
        from marvin import openai, settings

        try:
            api_key = openai.ChatCompletion().__config__.api_key
        except AttributeError:
            api_key = openai.ChatCompletion().request().api_key
        assert settings.openai.api_key.get_secret_value() == api_key

    def test_merge(self):
        from marvin.openai.ChatCompletion import ChatCompletionConfig

        functions = [lambda x: x]
        messages = [{"role": "user", "content": "Hello"}]
        config1 = ChatCompletionConfig(functions=functions, messages=messages)
        config2 = ChatCompletionConfig(functions=functions, messages=messages)
        config3 = config1.merge(**config2.dict())
        if isinstance(config3, dict):
            assert config3.get("functions") == functions * 2
            assert config3.get("messages") == messages * 2
        if isinstance(config3, ChatCompletionConfig):
            assert (
                config3.dict().get("functions") == config2.dict().get("functions") * 2
            )
            assert config3.messages == messages * 2


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
