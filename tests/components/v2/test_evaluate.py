from typing import Literal

import marvin.v2
import pytest

from tests.utils import pytest_mark_class


@pytest_mark_class("llm")
class TestEvaluate:
    @pytest.mark.parametrize(
        "objective, expected",
        [
            ("Finish the pattern. One, two, three...", "four"),
            ("Spell the answer to two plus two", "four"),
            ("What city is the capital of New York?", "Albany"),
        ],
    )
    def test_simple_objective(self, objective, expected):
        result = marvin.v2.evaluate(objective=objective)
        assert result == expected

    def test_list_fruit(self):
        result = marvin.v2.evaluate(
            objective="Generate a list of 3 fruit",
            response_model=list[str],
        )
        assert result == ["apple", "banana", "orange"]

    def test_list_fruit_with_context(self):
        result = marvin.v2.evaluate(
            objective="Generate a list of `n` fruit",
            response_model=list[str],
            context=dict(n=3),
        )
        assert result == ["apple", "banana", "orange"]

    def test_list_fruit_with_instructions(self):
        result = marvin.v2.evaluate(
            objective="Suggest a common fruit",
            response_model=str,
            instructions="only include fruit that are blue",
        )
        assert result == "Blueberry"

    def test_list_numbers(self):
        result = marvin.v2.evaluate(
            objective="Generate a list of 3 numbers",
            response_model=list[int],
        )
        assert result == [1, 2, 3]

    def test_identify_locations(self):
        result = marvin.v2.evaluate(
            objective="Identify the locations in these excerpts by their proper names",
            context=dict(
                excerpts=[
                    "I live in New York City",
                    "I live in NYC",
                    "I live in the big apple",
                    "I'm from chicago",
                ]
            ),
            response_model=list[str],
        )

        assert result == ["New York City", "New York City", "New York City", "Chicago"]

    def test_classify_sentiment(self):
        result = marvin.v2.evaluate(
            objective="Classify the sentiment of each of the phrases",
            response_model=list[Literal["positive", "negative", "neutral"]],
            context=dict(
                phrases=[
                    "I hate this",
                    "This is amazing",
                    "I don't know how I feel about this",
                ]
            ),
        )

        assert result == ["negative", "positive", "neutral"]

    def test_dict_response_model_origin(self):
        result = marvin.v2.evaluate(
            objective="Generate x/y coordinates for the origin",
            response_model=dict[str, int],
        )
        assert result == dict(x=0, y=0)

    def test_instructions_coordinates(self):
        result = marvin.v2.evaluate(
            objective="Generate x/y coordinates for the origin",
            instructions="add one to x and two to y",
            response_model=dict[str, int],
        )
        assert result == dict(x=1, y=2)
