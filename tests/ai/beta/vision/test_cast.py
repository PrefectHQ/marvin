import marvin
from pydantic import BaseModel, Field

from tests.utils import pytest_mark_class


@pytest_mark_class("llm")
class TestVisionCast:
    def test_cast_dog(self):
        class Animal(BaseModel):
            type: str = Field(description="The type of animal (cat, bird, etc.)")
            primary_color: str
            has_spots: bool

        img = "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg"
        result = marvin.cast_vision(images=[img], target=Animal)
        assert result == Animal(type="dog", primary_color="white", has_spots=True)

    def test_cast_ny(self):
        class Location(BaseModel):
            city: str
            state: str = Field(description="The two letter abbreviation")

        img = "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        result = marvin.cast_vision(img, target=Location)
        assert result == Location(city="New York", state="NY")

    def test_cast_book(self):
        class Book(BaseModel):
            title: str
            subtitle: str
            authors: list[str]

        img = "https://hastie.su.domains/ElemStatLearn/CoverII_small.jpg"
        result = marvin.cast_vision(img, target=Book)
        assert result == Book(
            title="The Elements of Statistical Learning",
            subtitle="Data Mining, Inference, and Prediction",
            authors=["Trevor Hastie", "Robert Tibshirani", "Jerome Friedman"],
        )
