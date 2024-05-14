import marvin
import pytest
from marvin.utilities.testing import assert_locations_equal
from pydantic import BaseModel, Field


class Location(BaseModel):
    city: str
    state: str = Field(description="The two letter abbreviation")


@pytest.fixture(autouse=True)
def use_gpt4o_for_all_tests(gpt_4):
    pass


@pytest.mark.flaky(max_runs=3)
class TestVisionCast:
    def test_cast_ny(self):
        img = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.cast(img, target=Location)
        assert_locations_equal(result, Location(city="New York", state="NY"))

    def test_cast_dc(self):
        img = marvin.Image(
            "https://images.unsplash.com/photo-1617581629397-a72507c3de9e"
        )
        result = marvin.cast(img, target=Location)
        assert isinstance(result, Location)
        assert_locations_equal(result, Location(city="Washington", state="DC"))

    def test_cast_ny_image_and_text(self):
        img = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.cast(
            data=["I see a tall building", img],
            target=Location,
        )
        assert_locations_equal(result, Location(city="New York", state="NY"))

    def test_cast_book(self):
        class Book(BaseModel):
            title: str
            subtitle: str
            authors: list[str]

        img = marvin.Image("https://hastie.su.domains/ElemStatLearn/CoverII_small.jpg")
        result = marvin.cast(img, target=Book)
        assert result == Book(
            title="The Elements of Statistical Learning",
            subtitle="Data Mining, Inference, and Prediction",
            authors=["Trevor Hastie", "Robert Tibshirani", "Jerome Friedman"],
        )


class TestAsync:
    async def test_cast_ny(self):
        img = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = await marvin.cast_async(img, target=Location)
        assert_locations_equal(result, Location(city="New York", state="NY"))


class TestMapping:
    def test_map(self):
        ny = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        dc = marvin.Image(
            "https://images.unsplash.com/photo-1617581629397-a72507c3de9e"
        )
        result = marvin.cast.map([ny, dc], target=Location)
        assert isinstance(result, list)
        assert_locations_equal(result[0], Location(city="New York", state="NY"))
        assert_locations_equal(result[1], Location(city="Washington", state="DC"))

    @pytest.mark.flaky(max_runs=2)
    async def test_async_map(self):
        ny = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        dc = marvin.Image(
            "https://images.unsplash.com/photo-1617581629397-a72507c3de9e"
        )
        result = await marvin.cast_async.map([ny, dc], target=Location)
        assert isinstance(result, list)

        assert_locations_equal(result[0], Location(city="New York", state="NY"))
        assert_locations_equal(result[1], Location(city="Washington", state="DC"))
