from enum import Enum

import pytest
from marvin.components import classifier
from typing_extensions import Literal

from tests.utils import pytest_mark_class

Sentiment = Literal["Positive", "Negative"]


class GitHubIssueTag(Enum):
    BUG = "bug"
    FEATURE = "feature"
    ENHANCEMENT = "enhancement"
    DOCS = "docs"


@pytest_mark_class("llm")
class TestClassifer:
    class TestLiteral:
        def test_classifier_literal_return_type(self):
            @classifier
            def sentiment(text: str) -> Sentiment:
                """Classify sentiment"""

            result = sentiment("Great!")

            assert result == "Positive"

        @pytest.mark.flaky(reruns=3)
        def test_classifier_literal_return_type_with_docstring(self):
            @classifier
            def sentiment(text: str) -> Sentiment:
                """Classify sentiment. Keep in mind it's opposite day"""

            result = sentiment("Great!")

            assert result == "Negative"

    class TestEnum:
        def test_classifier_enum_return_type(self):
            @classifier
            def labeler(text: str) -> GitHubIssueTag:
                """Classify GitHub issue tags"""

            result = labeler("the docs are trash, you slugs")

            assert result == GitHubIssueTag.DOCS
