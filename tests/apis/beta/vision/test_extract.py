from typing import Literal

import marvin
from pydantic import BaseModel

cat_dog_image = (
    "https://upload.wikimedia.org/wikipedia/commons/7/79/Trillium_Poncho_cat_dog.jpg"
)


class Animal(BaseModel, frozen=True):
    type: Literal["cat", "dog", "bird", "frog", "horse", "pig"]
    primary_color: Literal["white", "black", "gray", "blue", "golden"]


class TestVisionExtract:
    def test_cast_dog(self):
        result = marvin.ai.beta.vision.extract(images=[cat_dog_image], target=Animal)
        assert set(result) == {
            Animal(type="dog", primary_color="black"),
            Animal(type="cat", primary_color="gray"),
        }
