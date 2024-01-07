import marvin.v2
import pytest
from pydantic import BaseModel, Field

from tests.utils import pytest_mark_class


class Location(BaseModel):
    city: str = Field(description="The city's proper name")
    state: str = Field(description="2-letter state abbreviation")


@pytest_mark_class("llm")
class TestCast:
    class TestBuiltins:
        def test_cast_text_to_int(self):
            result = marvin.v2.cast("one", int)
            assert result == 1

        def test_cast_text_to_list_of_ints(self):
            result = marvin.v2.cast("one, TWO, three", list[int])
            assert result == [1, 2, 3]

        def test_cast_text_to_list_of_ints_2(self):
            result = marvin.v2.cast("4 and 5 then 6", list[int])
            assert result == [4, 5, 6]

        def test_cast_text_to_list_of_floats(self):
            result = marvin.v2.cast("1.1, 2.2, 3.3", list[float])
            assert result == [1.1, 2.2, 3.3]

        def test_cast_text_to_bool(self):
            result = marvin.v2.cast("no", bool)
            assert result is False

        def test_cast_text_to_bool_with_true(self):
            result = marvin.v2.cast("yes", bool)
            assert result is True

    class TestPydantic:
        @pytest.mark.parametrize("text", ["New York, NY", "NYC", "the big apple"])
        def test_cast_text_to_location(self, text, gpt_4):
            result = marvin.v2.cast(f"I live in {text}", Location)
            assert result == Location(city="New York", state="NY")

        def test_pay_attention_to_field_descriptions(self, gpt_4):
            # GPT-3.5 gets this wrong
            class Car(BaseModel):
                make: str = Field(description="The manufacturer, must ALWAYS be Ford")

            result = marvin.v2.cast("I bought a Chevrolet", Car)
            assert result == Car(make="Ford")

    class TestInstructions:
        def test_cast_text_with_significant_instructions(self):
            result = marvin.v2.cast("one", int, instructions="return the number 4")
            assert result == 4

        def test_cast_text_with_subtle_instructions(self, gpt_4):
            result = marvin.v2.cast(
                "My name is marvin",
                str,
                instructions="Rewrite with names (and only names) uppercase",
            )
            assert result == "My name is MARVIN"
