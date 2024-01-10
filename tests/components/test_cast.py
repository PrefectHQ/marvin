import marvin
import pytest
from pydantic import BaseModel, Field

from tests.utils import pytest_mark_class


class Location(BaseModel):
    city: str = Field(description="The city's proper name")
    state: str = Field(description="2-letter abbreviation")


@pytest_mark_class("llm")
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

    class TestPydantic:
        @pytest.mark.parametrize("text", ["New York, NY", "NYC", "the big apple"])
        def test_cast_text_to_location(self, text, gpt_4):
            result = marvin.cast(f"I live in {text}", Location)
            assert result == Location(city="New York", state="NY")

    class TestInstructions:
        def test_cast_text_with_significant_instructions(self):
            result = marvin.cast("one", int, instructions="return the number 4")
            assert result == 4

        def test_cast_text_with_subtle_instructions(self, gpt_4):
            result = marvin.cast(
                "My name is marvin",
                str,
                instructions="makes names uppercase",
            )
            assert result == "My name is MARVIN"
