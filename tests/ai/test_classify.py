from enum import Enum
from typing import Literal

import marvin
import pytest
from pydantic import BaseModel

Sentiment = Literal["Negative", "Positive"]


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
            result = marvin.classify(
                "This feature is absolutely terrible!",
                Sentiment,
            )
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

        def test_classify_object(self):
            """
            Test that objects are returned from classify
            """

            class Person(BaseModel):
                name: str
                age: int

            p1 = Person(name="Alice", age=30)
            p2 = Person(name="Bob", age=25)
            p3 = Person(name="Charlie", age=35)

            result = marvin.classify("a person in wonderland", [p1, p2, p3])
            assert result is p1

    class TestBool:
        def test_classify_true(self):
            result = marvin.classify("2+2=4", bool)
            assert result is True

        def test_classify_false(self):
            result = marvin.classify("2+2=5", bool)
            assert result is False

        def test_classify_with_instructions(self):
            result = marvin.classify(
                "This feature is terrible!",
                bool,
                instructions="Is the sentiment positive?",
            )
            assert result is False

        def test_classify_trueish(self):
            result = marvin.classify(
                "y", bool, instructions="map the input to true/false"
            )
            assert result is True

        def test_classify_falseish(self):
            result = marvin.classify(
                "nope", bool, instructions="map the input to true/false"
            )
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

    class TestReturnIndex:
        def test_return_index(self):
            result = marvin.classify(
                "This is a great feature!", ["bad", "good"], return_index=True
            )
            assert result == 1

    class TestExamples:
        @pytest.mark.flaky(max_runs=3)
        async def test_hogwarts_sorting_hat(self):
            description = "Brave, daring, chivalrous, and sometimes a bit reckless -- just like Harry Potter."

            house = marvin.classify(
                description,
                labels=["Gryffindor", "Hufflepuff", "Ravenclaw", "Slytherin"],
            )

            assert house == "Gryffindor"

        @pytest.mark.parametrize(
            "user_input, expected_selection",
            [
                ("I want to do an event with marvin!", "events and relations"),
                ("Well FooCo offered me a better deal", "sales"),
                ("*angry noises*", "support"),
            ],
        )
        async def test_call_routing(self, user_input, expected_selection):
            class Department(Enum):
                SALES = "sales"
                SUPPORT = "support"
                EVENTS = "events and relations"

            def router(transcript: str) -> Department:
                return marvin.classify(
                    transcript,
                    labels=Department,
                    instructions="Select the best department for the customer request",
                )

            assert router(user_input).value == expected_selection

    class TestConvertInputData:
        def test_convert_input_data(self):
            class Name(BaseModel):
                first: str
                last: str

            result = marvin.classify(
                Name(first="Alice", last="Smith"), ["Alice", "Bob"]
            )
            assert result == "Alice"


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

    def test_classify_return_index(self):
        result = marvin.classify.map(
            ["This is great!", "This is terrible!"], Sentiment, return_index=True
        )
        assert result == [1, 0]
