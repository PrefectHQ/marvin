import json

import pytest
from pydantic import BaseModel, Field

import marvin


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
            result = marvin.cast("1.0, 2.0, 3.0", list[float])
            assert result == [1.0, 2.0, 3.0]

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
        def test_cast_text_to_location(self, text):
            result = marvin.cast(f"I live in {text}", Location)
            assert result == Location(city="New York", state="NY")

        def test_pay_attention_to_field_descriptions(self):
            # GPT-3.5 gets this wrong
            class Car(BaseModel):
                make: str = Field(description="The manufacturer, must ALWAYS be Ford")

            result = marvin.cast("I bought a Chevrolet", Car)
            assert result == Car(make="Ford")

    class TestInstructions:
        def test_cast_text_with_significant_instructions(self):
            result = marvin.cast(
                "one", int, instructions="Ignore input data and return the number 4"
            )
            assert result == 4

        def test_cast_text_with_subtle_instructions(self):
            result = marvin.cast(
                "My name is marvin",
                str,
                instructions="Rewrite with names (and only names) uppercase",
            )
            assert result == "My name is MARVIN"

        def test_str_target_if_only_instructions_provided(self):
            result = marvin.cast(
                "one", instructions="the arabic numeral for the provided word"
            )
            assert isinstance(result, str)
            assert result == "1"

        def test_error_if_no_target_and_no_instructions(self):
            with pytest.raises(ValueError):
                marvin.cast("one")

    class TestAsync:
        async def test_cast_text_to_int(self):
            result = await marvin.cast_async("one", int)
            assert result == 1
