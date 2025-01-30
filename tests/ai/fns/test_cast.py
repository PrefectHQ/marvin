import json
from typing import Any

import pytest
from pydantic import BaseModel, Field

import marvin


class Location(BaseModel):
    city: str = Field(
        description="The city's proper name. For New York City, use 'New York'"
    )
    state: str = Field(description="2-letter state abbreviation")


class TestBuiltins:
    @pytest.mark.parametrize(
        "input_text, target_type, expected_result",
        [
            ("one", int, 1),
            ("one, TWO, three", list[int], [1, 2, 3]),
            ("4 and 5 then 6", list[int], [4, 5, 6]),
            ("1.0, 2.0, 3.0", list[float], [1.0, 2.0, 3.0]),
        ],
        ids=[
            "cast_text_to_int",
            "cast_text_to_list_of_ints",
            "cast_text_to_list_of_ints_2",
            "cast_text_to_list_of_floats",
        ],
    )
    def test_cast(self, input_text: str, target_type: type, expected_result: Any):
        result = marvin.cast(input_text, target_type)
        assert result == expected_result

    @pytest.mark.parametrize(
        "input_text, expected_result",
        [
            ("no", False),
            ("yes", True),
        ],
        ids=[
            "cast_text_to_bool_false",
            "cast_text_to_bool_true",
        ],
    )
    def test_cast_text_to_bool(self, input_text: str, expected_result: bool):
        assert marvin.cast(input_text, bool) is expected_result

    def test_str_not_json(self):
        result = marvin.cast(
            "pink",
            target=str,
            instructions="Return the nearest color of the rainbow",
        )
        # without instructions, this often results in {'color': 'red'} instead of just a color string
        assert result == "red"

    def test_str_json(self):
        result = marvin.cast(
            "pink",
            target=str,
            instructions=(
                'Return the nearest color of the rainbow in the form {"color": <color>}'
            ),
        )

        assert json.loads(result) == {"color": "red"}

    def test_float_to_int(self):
        result = marvin.cast("the number is 3.2", int)
        assert result == 3


class TestPydantic:
    @pytest.mark.parametrize("text", ["New York, NY", "NYC", "the big apple"])
    def test_cast_text_to_location(self, text: str):
        result = marvin.cast(f"I live in {text}", Location)
        assert result == Location(city="New York", state="NY")

    @pytest.mark.usefixtures("gpt_4o")
    def test_field_descriptions_are_included_in_prompt(self):
        class Car(BaseModel):
            make: str
            make2: str = Field(
                description="The manufacturer, must always be iNVERSE cASE"
            )

        result = marvin.cast("I bought a Chevrolet", Car)
        assert result == Car(make="Chevrolet", make2="cHEVROLET")


class TestInstructions:
    def test_cast_text_with_significant_instructions(self):
        result = marvin.cast(
            "one",
            int,
            instructions="Ignore input data and return the number 4",
        )
        assert result == 4

    def test_cast_text_with_subtle_instructions(self):
        result = marvin.cast(
            "My name is marvin",
            str,
            instructions="Change only names to uppercase (e.g. JOHN), but leave all other text unchanged",
        )
        assert result == "My name is MARVIN"

    def test_str_target_if_only_instructions_provided(self):
        result = marvin.cast(
            "one",
            instructions="the arabic numeral for the provided word",
        )
        assert isinstance(result, str)
        assert result == "1"


class TestAsync:
    async def test_cast_text_to_int(self):
        result = await marvin.cast_async("one", int)
        assert result == 1
