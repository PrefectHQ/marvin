import marvin
import pytest
from pydantic import BaseModel, Field

from tests.utils import pytest_mark_class


class Location(BaseModel):
    city: str = Field(description="The city's proper name")
    state: str = Field(description="2-letter abbreviation")


@pytest_mark_class("llm")
class TestExtract:
    class TestBuiltins:
        def test_extract_numbers(self):
            result = marvin.extract("one, TWO, three", int)
            assert result == [1, 2, 3]

        def test_extract_complex_numbers(self, gpt_4):
            result = marvin.extract(
                "I paid $10 for 3 coffees and they gave me back a dollar and 25 cents",
                float,
            )
            assert result == [10.0, 3.0, 1.25]

        def test_extract_money(self):
            result = marvin.extract(
                "I paid $10 for 3 coffees and they gave me back a dollar and 25 cents",
                float,
                instructions="money",
            )
            assert result == [10.0, 1.25]

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

        def test_extract_multiple_locations_by_nickname(self, gpt_4):
            result = marvin.extract("I live in the big apple and work in SF", Location)
            assert result == [
                Location(city="New York", state="NY"),
                Location(city="San Francisco", state="CA"),
            ]

        @pytest.mark.xfail(reason="tuples aren't working right now")
        def test_extract_complex_pattern(self, gpt_4):
            result = marvin.extract(
                "John lives in Boston, Mary lives in NYC, and I live in SF",
                tuple[str, Location],
                instructions="pair names and locations",
            )
            assert result == []
