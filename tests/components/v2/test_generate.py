import marvin.v2
from pydantic import BaseModel, Field

from tests.utils import pytest_mark_class


class Location(BaseModel):
    city: str = Field(description="The city's proper name")
    state: str = Field(description="2-letter state abbreviation")


@pytest_mark_class("llm")
class TestCast:
    class TestBuiltins:
        def test_toy_generate(self):
            result = marvin.v2.generate(
                int, n=3, instructions="always generate the first 3 integers"
            )
            assert result == [1, 2, 3]
