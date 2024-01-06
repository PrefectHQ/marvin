from enum import Enum
from typing import Literal

import marvin.v2

from tests.utils import pytest_mark_class

Sentiment = Literal["Positive", "Negative"]


class GitHubIssueTag(Enum):
    BUG = "bug"
    FEATURE = "feature"
    ENHANCEMENT = "enhancement"
    DOCS = "docs"


@pytest_mark_class("llm")
class TestClassify:
    class TestLiteral:
        def test_classify_sentiment(self):
            result = marvin.v2.classify("This is a great feature!", Sentiment)
            assert result == "Positive"

        def test_classify_negative_sentiment(self):
            result = marvin.v2.classify("This feature is terrible!", Sentiment)
            assert result == "Negative"

    class TestEnum:
        def test_classify_bug_tag(self):
            result = marvin.v2.classify("This is a bug", GitHubIssueTag)
            assert result == GitHubIssueTag.BUG

        def test_classify_feature_tag(self):
            result = marvin.v2.classify("This is a great feature!", GitHubIssueTag)
            assert result == GitHubIssueTag.FEATURE

        def test_classify_enhancement_tag(self):
            result = marvin.v2.classify("This is an enhancement", GitHubIssueTag)
            assert result == GitHubIssueTag.ENHANCEMENT

        def test_classify_docs_tag(self):
            result = marvin.v2.classify(
                "This is a documentation update", GitHubIssueTag
            )
            assert result == GitHubIssueTag.DOCS

    class TestInstructions:
        def test_classify_positive_sentiment_with_instructions(self):
            result = marvin.v2.classify(
                "This is a great feature!", Sentiment, instructions="It's opposite day."
            )
            assert result == "Negative"
