import pytest
from dirty_equals import IsPartialDict
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

import marvin
from marvin.utilities.jsonschema import jsonschema_to_type
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


class TestGenerateSchema:
    async def test_generate_list_of_integers_schema(self):
        result = await marvin.generate_schema_async(
            instructions="a list that containsexactly three integers",
        )
        assert result == {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 3,
            "maxItems": 3,
        }

        schema_type = jsonschema_to_type(result)
        assert TypeAdapter(schema_type).validate_python([1, 2, 3])
        with pytest.raises(ValidationError):
            TypeAdapter(schema_type).validate_python([1, 2])
        with pytest.raises(ValidationError):
            TypeAdapter(schema_type).validate_python([1, 2, 3, 4])

    async def test_generate_schema_for_movie(self):
        result = await marvin.generate_schema_async(
            instructions="a movie with a title, director, and release_year",
        )
        assert result == IsPartialDict(
            {
                "type": "object",
                "properties": IsPartialDict(
                    {
                        "title": {"type": "string"},
                        "director": {"type": "string"},
                        "release_year": {"type": "integer"},
                    }
                ),
                "required": ["title", "director", "release_year"],
            }
        )

    async def test_generate_schema_with_base_schema(self):
        base_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "director": {"type": "string"},
            },
            "required": ["title"],
        }
        result = await marvin.generate_schema_async(
            instructions="add a release_year",
            base_schema=base_schema,
        )
        assert result == IsPartialDict(
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "director": {"type": "string"},
                    "release_year": {"type": "integer"},
                },
                "required": ["title"],
            }
        )

    async def test_generate_schema_with_base_schema_and_required_instruction(self):
        base_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "director": {"type": "string"},
            },
            "required": ["title"],
        }
        result = await marvin.generate_schema_async(
            instructions="add a release_year, and make it required",
            base_schema=base_schema,
        )
        assert result == IsPartialDict(
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "director": {"type": "string"},
                    "release_year": {"type": "integer"},
                },
                "required": ["title", "release_year"],
            }
        )
