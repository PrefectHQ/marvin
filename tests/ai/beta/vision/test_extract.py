from typing import Literal

import marvin
from marvin.utilities.testing import assert_equal
from pydantic import BaseModel


class TestVisionExtract:
    def test_dog(self):
        class Animal(BaseModel, frozen=True):
            type: Literal["cat", "dog", "bird", "frog", "horse", "pig"]
            primary_color: Literal["white", "black", "gray", "blue", "golden"]

        img = "https://upload.wikimedia.org/wikipedia/commons/7/79/Trillium_Poncho_cat_dog.jpg"
        result = marvin.extract_vision(images=[img], target=Animal)
        assert set(result) == {
            Animal(type="dog", primary_color="black"),
            Animal(type="cat", primary_color="gray"),
        }

    def test_dog_breeds(self):
        img = "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?q=80&w=2969&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
        result = marvin.extract_vision(img, target=str, instructions="dog breeds")
        assert_equal(result, ["Pembroke Welsh Corgi", "Yorkshire Terrier"])
