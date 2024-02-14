import json
from enum import Enum
from unittest.mock import patch

import marvin
import pytest
from pydantic import BaseModel, Field


class Location(BaseModel):
    city: str = Field(description="The city's proper name")
    state: str = Field(description="2-letter state abbreviation")


class TestCast:
    class TestBuiltins:
        def test_cast_text_to_int(self):
            result = marvin.cast("one", int)
            assert result == 1

        def test_cast_text_to_list_of_ints(self):
            result = marvin.cast("one, TWO, three", list[int])
            assert result == [1, 2, 3]

        def test_cast_text_to_list_of_ints_2(self):
            result = marvin.cast("4 and 5 then 6", list[int])
            assert result == [4, 5, 6]

        def test_cast_text_to_list_of_floats(self):
            result = marvin.cast("1.1, 2.2, 3.3", list[float])
            assert result == [1.1, 2.2, 3.3]

        def test_cast_text_to_bool(self):
            result = marvin.cast("no", bool)
            assert result is False

        def test_cast_text_to_bool_with_true(self):
            result = marvin.cast("yes", bool)
            assert result is True

        def test_str_not_json(self):
            result = marvin.cast(
                "pink",
                target=str,
                instructions="Return the nearest color of the rainbow",
            )
            # without instructions, this often results in {'color': 'red'} instead of just a color string
            assert result == "red"

        def test_str_json(self, gpt_4):
            result = marvin.cast(
                "pink",
                target=str,
                instructions=(
                    "Return the nearest color of the rainbow (as a JSON"
                    " object with a `color` key)"
                ),
            )

            assert json.loads(result) == {"color": "red"}

        def test_float_to_int(self):
            result = marvin.cast("the number is 3.2", int)
            assert result == 3

    class TestPydantic:
        @pytest.mark.parametrize("text", ["New York, NY", "NYC", "the big apple"])
        def test_cast_text_to_location(self, text, gpt_4):
            result = marvin.cast(f"I live in {text}", Location)
            assert result in (
                Location(city="New York", state="NY"),
                Location(city="New York City", state="NY"),
            )

        def test_pay_attention_to_field_descriptions(self, gpt_4):
            # GPT-3.5 gets this wrong
            class Car(BaseModel):
                make: str = Field(description="The manufacturer, must ALWAYS be Ford")

            result = marvin.cast("I bought a Chevrolet", Car)
            assert result == Car(make="Ford")

    class TestInstructions:
        def test_cast_text_with_significant_instructions(self):
            result = marvin.cast("one", int, instructions="return the number 4")
            assert result == 4

        def test_cast_text_with_subtle_instructions(self, gpt_4):
            result = marvin.cast(
                "My name is marvin",
                str,
                instructions="Rewrite with names (and only names) uppercase",
            )
            assert result == "My name is MARVIN"

    class TestCastCallsClassify:
        @patch("marvin.ai.text.classify_async")
        def test_cast_doesnt_call_classify_for_int(self, mock_classify):
            marvin.cast("Yes", int)
            mock_classify.assert_not_called()

        @patch("marvin.ai.text.classify_async")
        def test_cast_calls_classify_for_bool(self, mock_classify):
            marvin.cast("Yes", bool)
            mock_classify.assert_called_once()

        @patch("marvin.ai.text.classify_async")
        def test_cast_calls_classify_for_enum(self, mock_classify):
            class Sentiment(Enum):
                positive = "Positive"
                negative = "Negative"

            marvin.cast("Yes", Sentiment)

            mock_classify.assert_called_once()

    class TestAsync:
        async def test_cast_text_to_int(self):
            result = await marvin.cast_async("one", int)
            assert result == 1


class TestMapping:
    def test_cast_map(self):
        result = marvin.cast.map(["one", "two"], int)
        assert isinstance(result, list)
        assert result == [1, 2]

    def test_cast_map_with_instructions(self):
        result = marvin.cast.map(
            ["one", "two"],
            int,
            instructions="add one to each number",
        )
        assert isinstance(result, list)
        assert result == [2, 3]

    async def test_async_cast_map(self):
        result = await marvin.cast_async.map(["one", "two"], int)
        assert isinstance(result, list)
        assert result == [1, 2]
