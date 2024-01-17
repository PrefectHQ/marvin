import marvin
import pytest
from pydantic import BaseModel, Field


class Location(BaseModel):
    city: str = Field(description="The city's proper name")
    state: str = Field(description="2-letter abbreviation")


class TestExtract:
    class TestBuiltins:
        def test_extract_numbers(self):
            result = marvin.extract("one, two, three", int)
            assert result == [1, 2, 3]

        def test_extract_complex_numbers(self):
            result = marvin.extract(
                "I paid $10 for 3 coffees and they gave me back a dollar and 25 cents",
                float,
            )
            if marvin.settings.openai.chat.completions.model.startswith("gpt-3.5"):
                assert result == [10.0, 3.0, 1.25]
            else:
                assert result == [10.0, 1.25]

        def test_extract_money(self):
            result = marvin.extract(
                "I paid $10 for 3 coffees and they gave me back a dollar and 25 cents",
                float,
                instructions="dollar amounts",
            )
            assert result == [10.0, 1.25]

        def test_extract_names(self):
            result = marvin.extract(
                "My name is John, my friend's name is Mary, and my other friend's name"
                " is Bob",
                str,
                instructions="names",
            )
            assert result == ["John", "Mary", "Bob"]

        @pytest.mark.flaky(max_runs=3)
        def test_float_to_int(self):
            # gpt 3.5 sometimes struggles with this test, marked as flaky
            # pydantic no longer casts floats to ints, but gpt-3.5 assumes it's
            # ok even when given instructions not to. GPT-4 seems to work ok.
            result = marvin.extract("the numbers are 1, 2, and 3.2", int)
            assert result == [1, 2, 3]

    class TestInstructions:
        def test_city_and_state(self):
            result = marvin.extract(
                "I live in the big apple",
                str,
                instructions="(city, state abbreviation)",
            )
            assert result == ["New York, NY"]

    class TestPydantic:
        def test_extract_location(self):
            result = marvin.extract("I live in New York, NY", Location)
            assert result == [Location(city="New York", state="NY")]

        def test_extract_multiple_locations(self):
            result = marvin.extract(
                "I live in New York, NY and work in San Francisco, CA", Location
            )
            assert result == [
                Location(city="New York", state="NY"),
                Location(city="San Francisco", state="CA"),
            ]

        def test_extract_multiple_locations_by_nickname(self):
            result = marvin.extract("I live in the big apple and work in SF", Location)
            assert result == [
                Location(city="New York", state="NY"),
                Location(city="San Francisco", state="CA"),
            ]

        @pytest.mark.xfail(reason="tuples aren't working right now")
        def test_extract_complex_pattern(self):
            result = marvin.extract(
                "John lives in Boston, Mary lives in NYC, and I live in SF",
                tuple[str, Location],
                instructions="pair names and locations",
            )
            assert result == []
