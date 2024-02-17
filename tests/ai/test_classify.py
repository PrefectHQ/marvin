from enum import Enum
from typing import Literal

import marvin
import pytest

Sentiment = Literal["Positive", "Negative"]


class GitHubIssueTag(Enum):
    BUG = "bug"
    FEATURE = "feature"
    ENHANCEMENT = "enhancement"
    DOCS = "docs"


class TestClassify:
    class TestLiteral:
        def test_classify_sentiment(self):
            result = marvin.classify("This is a great feature!", Sentiment)
            assert result == "Positive"

        def test_classify_negative_sentiment(self):
            result = marvin.classify("This feature is terrible!", Sentiment)
            assert result == "Negative"

    class TestEnum:
        def test_classify_bug_tag(self):
            result = marvin.classify("This is a bug", GitHubIssueTag)
            assert result == GitHubIssueTag.BUG

        def test_classify_feature_tag(self):
            result = marvin.classify("This is a great feature!", GitHubIssueTag)
            assert result == GitHubIssueTag.FEATURE

        def test_classify_enhancement_tag(self):
            result = marvin.classify("This is an enhancement", GitHubIssueTag)
            assert result == GitHubIssueTag.ENHANCEMENT

        def test_classify_docs_tag(self):
            result = marvin.classify("This is a documentation update", GitHubIssueTag)
            assert result == GitHubIssueTag.DOCS

    class TestList:
        def classify_bug_tag(self):
            result = marvin.classify(
                "This is a bug", ["bug", "feature", "enhancement", "docs"]
            )
            assert result == "bug"

        def test_classify_number(self):
            # a version of the prompt would choose the label *number* that
            # matched the data, rather than the label *description*
            result = marvin.classify(0, ["letter", "number"])
            assert result == "number"

    class TestBool:
        def test_classify_positive_sentiment(self):
            result = marvin.classify("This is a great feature!", bool)
            assert result is True

        def test_classify_negative_sentiment(self):
            result = marvin.classify("This feature is terrible!", bool)
            assert result is False

        def test_classify_falseish(self):
            result = marvin.classify("nope", bool)
            assert result is False

    class TestInstructions:
        def test_classify_positive_sentiment_with_instructions(self):
            result = marvin.classify(
                "This is a great feature!", Sentiment, instructions="It's opposite day."
            )
            assert result == "Negative"

    class TestAsync:
        async def test_classify_positive_sentiment(self):
            result = await marvin.classify_async("This is a great feature!", bool)
            assert result is True

    class TestExamples:
        async def test_hogwarts_sorting_hat(self):
            description = "Brave, daring, chivalrous, and sometimes a bit reckless."

            house = marvin.classify(
                description,
                labels=["Gryffindor", "Hufflepuff", "Ravenclaw", "Slytherin"],
            )

            assert house == "Gryffindor"

        @pytest.mark.parametrize(
            "user_input, expected_selection",
            [
                ("I need to update my payment method", "billing"),
                ("Well FooCo offered me a better deal", "sales"),
                ("*angry noises*", "support"),
            ],
        )
        async def test_call_routing(self, user_input, expected_selection):
            class Department(Enum):
                SALES = "sales"
                SUPPORT = "support"
                BILLING = "billing"

            def router(transcript: str) -> Department:
                return marvin.classify(
                    transcript,
                    labels=Department,
                    instructions="Select the best department for the customer request",
                )

            assert router(user_input).value == expected_selection


class TestMapping:
    def test_classify_map(self):
        result = marvin.classify.map(["This is great!", "This is terrible!"], Sentiment)
        assert isinstance(result, list)
        assert result == ["Positive", "Negative"]

    def test_classify_map_with_instructions(self, gpt_4):
        result = marvin.classify.map(
            ["o", "0"],
            ["letter", "number"],
            instructions="'o' means zero",
        )
        assert isinstance(result, list)
        assert result == ["number", "number"]

    async def test_async_classify_map(self):
        result = await marvin.classify_async.map(
            ["This is great!", "This is terrible!"], Sentiment
        )
        assert isinstance(result, list)
        assert result == ["Positive", "Negative"]
