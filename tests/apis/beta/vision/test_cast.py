import marvin
from pydantic import BaseModel, Field

dog_image = "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg"


class Animal(BaseModel):
    type: str = Field(description="The type of animal (cat, bird, etc.)")
    primary_color: str
    has_spots: bool


class TestVisionCast:
    def test_cast_dog(self):
        result = marvin.ai.beta.vision.cast(images=[dog_image], target=Animal)
        assert result == Animal(type="dog", primary_color="white", has_spots=True)
