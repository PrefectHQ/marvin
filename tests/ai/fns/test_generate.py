import pytest
from pydantic import BaseModel, Field

import marvin
from marvin.utilities.testing import assert_llm_equal


class Location(BaseModel):
    city: str = Field(description="The city's proper name")
    state: str = Field(description="2-letter state abbreviation")


class TestBuiltins:
    async def test_toy_generate(self):
        result = await marvin.generate_async(int, n=3)
        await assert_llm_equal(result, "a list of three integers")

    async def test_generate_locations(self):
        result = await marvin.generate_async(Location, n=3)
        await assert_llm_equal(result, "a list of three locations")

    async def test_generate_locations_with_instructions(self):
        result = await marvin.generate_async(
            Location,
            n=3,
            instructions="major cities in California",
        )
        await assert_llm_equal(
            result,
            "a list of three different locations that are major cities in California",
        )
        assert all(isinstance(loc, Location) for loc in result)

    async def test_error_if_no_type_or_instructions(self):
        with pytest.raises(ValueError, match="Instructions are required"):
            await marvin.generate_async(n=3)

    async def test_type_is_string_if_only_instructions_given(self):
        result = await marvin.generate_async(
            instructions="major cities in California", n=2
        )
        await assert_llm_equal(
            result,
            "a list of two major cities in California, both given as strings",
        )
