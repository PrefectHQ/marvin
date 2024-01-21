from typing import Literal

import marvin
import pytest
from marvin.utilities.testing import assert_equal
from pydantic import BaseModel, Field


class Location(BaseModel):
    city: str
    state: str = Field(description="The two letter abbreviation")


@pytest.mark.flaky(max_runs=2)
class TestVisionExtract:
    def test_ny(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.extract(img, target=Location)
        assert result in (
            [Location(city="New York", state="NY")],
            [Location(city="New York City", state="NY")],
        )

    def test_ny_images_input(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.extract(data=None, images=[img], target=Location)
        assert result in (
            [Location(city="New York", state="NY")],
            [Location(city="New York City", state="NY")],
        )

    def test_ny_image_input(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.extract(data=img, target=Location)
        assert result in (
            [Location(city="New York", state="NY")],
            [Location(city="New York City", state="NY")],
        )

    def test_ny_image_and_text(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.extract(
            data="I see the empire state building",
            images=[img],
            target=Location,
        )
        assert result in (
            [Location(city="New York", state="NY")],
            [Location(city="New York City", state="NY")],
        )

    def test_dog(self):
        class Animal(BaseModel, frozen=True):
            type: Literal["cat", "dog", "bird", "frog", "horse", "pig"]
            primary_color: Literal["white", "black", "blue", "golden"]

        img = marvin.beta.Image(
            "https://upload.wikimedia.org/wikipedia/commons/7/79/Trillium_Poncho_cat_dog.jpg"
        )
        result = marvin.beta.extract(img, target=Animal)
        assert set(result) == {
            Animal(type="dog", primary_color="black"),
            Animal(type="cat", primary_color="white"),
        }

    def test_dog_breeds(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?q=80&w=2969&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
        )
        result = marvin.beta.extract(img, target=str, instructions="dog breeds")
        assert_equal(
            result,
            "A list of two breeds that is roughly [Pembroke Welsh Corgi, Yorkshire"
            " Terrier] though exact results may vary, especially for the Terrier."
            " 'Terrier', 'mixed breed', or similar is ok.",
        )
