from enum import Enum

import pytest
from marvin import ai_classifier
from marvin.llms.providers import chat_llm

from tests.utils.mark import pytest_mark_class


class TestAIClassifiersInitialization:
    def test_model(self):
        @ai_classifier(model=chat_llm("openai/gpt-4-test-model"))
        class Sentiment(Enum):
            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        assert Sentiment.__model__.model == "gpt-4-test-model"

    def test_invalid_model(self):
        @ai_classifier(model=chat_llm("anthropic/claude-2"))
        class Sentiment(Enum):
            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        with pytest.raises(ValueError, match="(only compatible with OpenAI models)"):
            Sentiment("Great!")


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
            Sentiment("Great!", instructions="It's opposite day") == Sentiment.NEGATIVE
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

    def test_mapping_with_instructions(self):
        @ai_classifier
        class Sentiment(Enum):
            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        result = Sentiment.map(["good", "bad"], instructions="It's opposite day")
        assert result == [Sentiment.NEGATIVE, Sentiment.POSITIVE]
