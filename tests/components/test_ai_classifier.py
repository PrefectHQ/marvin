from enum import Enum

import pytest
from marvin import ai_classifier
from typing_extensions import Literal

from tests.utils import pytest_mark_class

Sentiment = Literal["Positive", "Negative"]


class GitHubIssueTag(Enum):
    BUG = "bug"
    FEATURE = "feature"
    ENHANCEMENT = "enhancement"
    DOCS = "docs"


@pytest_mark_class("llm")
class TestAIClassifer:
    class TestLiteral:
        def test_ai_classifier_literal_return_type(self):
            @ai_classifier
            def sentiment(text: str) -> Sentiment:
                """Classify sentiment"""

            result = sentiment("Great!")

            assert result == "Positive"

        def test_ai_classifier_literal_return_type_with_docstring(self):
            @ai_classifier
            def sentiment(text: str) -> Sentiment:
                """Classify sentiment - also its opposite day"""

            result = sentiment("Great!")

            assert result == "Negative"

    class TestEnum:
        def test_ai_classifier_enum_return_type(self):
            @ai_classifier
            def labeler(text: str) -> GitHubIssueTag:
                """Classify GitHub issue tags"""

            result = labeler("improve the docs you slugs")

            assert result == GitHubIssueTag.DOCS

    class TestList:
        @pytest.mark.skip(reason="TODO: fix this")
        def test_ai_classifier_list_return_type(self):
            @ai_classifier
            def labeler(text: str) -> list[str]:
                """Select from the following GitHub issue tags

                - bug
                - feature
                - enhancement
                - docs
                """

            result = labeler("i found a bug in the example from the docs")

            assert set(result) == {"bug", "docs"}
