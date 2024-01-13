import marvin
import pytest
from marvin.utilities.testing import assert_equal
from pydantic import BaseModel, Field

from tests.utils import pytest_mark_class


class Location(BaseModel):
    city: str = Field(description="The city's proper name")
    state: str = Field(description="2-letter state abbreviation")


@pytest_mark_class("llm")
class TestGenerate:
    class TestBuiltins:
        def test_toy_generate(self):
            result = marvin.generate(int, n=3)
            assert_equal(result, "a list of three integers")

        def test_generate_locations(self):
            result = marvin.generate(Location, n=3)
            assert_equal(result, "a list of three locations")

        def test_generate_locations_with_instructions(self):
            result = marvin.generate(
                Location, n=3, instructions="major cities in California"
            )
            assert_equal(
                result, "a list of three locations that are major cities in California"
            )

        def test_error_if_no_type_or_instructions(self):
            with pytest.raises(ValueError):
                marvin.generate(n=3)

        def test_type_is_string_if_only_instructions_given(self):
            result = marvin.generate(instructions="major cities in California", n=2)
            assert_equal(
                result,
                "a list of two major cities in California, both given as strings",
            )
