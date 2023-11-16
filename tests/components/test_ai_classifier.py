from enum import Enum

import pytest

try:
    from marvin import ai_classifier
except ImportError:
    pytest.skip("TODO: add new ai_classifier tests", allow_module_level=True)

from tests.utils import pytest_mark_class


class TestAIClassifiersInitialization:
    def test_model(self):
        @ai_classifier(model="openai/gpt-4-test-model")
        class Sentiment(Enum):
            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        assert (
            Sentiment.as_chat_completion("test").defaults.get("model")
            == "gpt-4-test-model"
        )

    def test_invalid_model(self):
        @ai_classifier(model="anthropic/claude-2")
        class Sentiment(Enum):
            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        assert Sentiment.as_chat_completion("test").defaults.get("model") == "claude-2"


@pytest_mark_class("llm")
class TestAIClassifiers:
    def test_sentiment(self):
        @ai_classifier
        class Sentiment(Enum):
            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        assert Sentiment("Great!") == Sentiment.POSITIVE

    def test_keys_are_passed_to_llm(self):
        @ai_classifier
        class Sentiment(Enum):
            POSITIVE = "option - 1"
            NEGATIVE = "option - 2"

        assert Sentiment("Great!") == Sentiment.POSITIVE

    def test_values_are_passed_to_llm(self):
        @ai_classifier
        class Sentiment(Enum):
            OPTION_1 = "Positive"
            OPITION_2 = "Negative"

        assert Sentiment("Great!") == Sentiment.OPTION_1

    def test_docstring_is_passed_to_llm(self):
        @ai_classifier
        class Sentiment(Enum):
            """It's opposite day"""

            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        assert Sentiment("Great!") == Sentiment.NEGATIVE

    def test_instructions_are_passed_to_llm(self):
        @ai_classifier
        class Sentiment(Enum):
            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        assert (
            Sentiment("Great!", instructions="today is opposite day")
            == Sentiment.NEGATIVE
        )

    def test_recover_complex_values(self):
        @ai_classifier
        class Sentiment(Enum):
            POSITIVE = {"value": "Positive"}
            NEGATIVE = {"value": "Negative"}

        result = Sentiment("Great!")

        assert result.value["value"] == "Positive"


@pytest_mark_class("llm")
class TestMapping:
    def test_mapping(self):
        @ai_classifier
        class Sentiment(Enum):
            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        result = Sentiment.map(["good", "bad"])
        assert result == [Sentiment.POSITIVE, Sentiment.NEGATIVE]

    @pytest.mark.xfail(reason="Flaky with 3.5 turbo")
    def test_mapping_with_instructions(self):
        @ai_classifier
        class Sentiment(Enum):
            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        result = Sentiment.map(
            ["good", "bad"], instructions="I want the opposite of the right answer"
        )
        assert result == [Sentiment.NEGATIVE, Sentiment.POSITIVE]
