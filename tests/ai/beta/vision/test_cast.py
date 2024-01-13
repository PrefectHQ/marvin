import marvin
import pytest
from pydantic import BaseModel, Field

from tests.utils import pytest_mark_class


class Location(BaseModel):
    city: str
    state: str = Field(description="The two letter abbreviation")


@pytest.mark.flaky(max_runs=2)
@pytest_mark_class("llm")
class TestVisionCast:
    def test_cast_ny(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.cast(img, target=Location)
        assert result == Location(city="New York", state="NY")

    def test_cast_ny_images_input(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.cast(data=None, images=[img], target=Location)
        assert result == Location(city="New York", state="NY")

    def test_cast_ny_image_input(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.cast(data=img, target=Location)
        assert result == Location(city="New York", state="NY")

    def test_cast_ny_image_and_text(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.cast(
            data="I see the empire state building",
            images=[img],
            target=Location,
        )
        assert result == Location(city="New York", state="NY")

    def test_cast_dog(self):
        class Animal(BaseModel):
            type: str = Field(description="The type of animal (cat, bird, etc.)")
            primary_color: str
            has_spots: bool

        img = marvin.beta.Image(
            "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg"
        )
        result = marvin.beta.cast(img, target=Animal)
        assert result == Animal(type="dog", primary_color="white", has_spots=True)

    def test_cast_book(self):
        class Book(BaseModel):
            title: str
            subtitle: str
            authors: list[str]

        img = marvin.beta.Image(
            "https://hastie.su.domains/ElemStatLearn/CoverII_small.jpg"
        )
        result = marvin.beta.cast(img, target=Book)
        assert result == Book(
            title="The Elements of Statistical Learning",
            subtitle="Data Mining, Inference, and Prediction",
            authors=["Trevor Hastie", "Robert Tibshirani", "Jerome Friedman"],
        )
