from enum import Enum

import pytest
from marvin import ai_classifier
from marvin.engine.language_models import chat_llm


class TestAIClassifiers:
    def test_invalid_model(self):
        @ai_classifier(model=chat_llm("anthropic/claude-2"))
        class Sentiment(Enum):
            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        with pytest.raises(ValueError, match="(only compatible with OpenAI models)"):
            Sentiment("Great!")

    def test_invalid_max_tokens(self):
        @ai_classifier(model=chat_llm("openai/gpt-4", max_tokens=100))
        class Sentiment(Enum):
            POSITIVE = "Positive"
            NEGATIVE = "Negative"

        with pytest.raises(ValueError, match="(max_tokens=1)"):
            Sentiment("Great!")
