import marvin

from tests.utils import pytest_mark_class


@pytest_mark_class("llm")
class TestVisionClassify:
    def test_ny(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.classify(img, labels=["urban", "rural"])
        assert result == "urban"

    def test_ny_images_input(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.classify(
            data=None, images=[img], labels=["urban", "rural"]
        )
        assert result == "urban"

    def test_ny_image_input(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.classify(data=img, labels=["urban", "rural"])
        assert result == "urban"

    def test_ny_image_and_text(self):
        img = marvin.beta.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.beta.classify(
            data="I see the empire state building",
            images=[img],
            labels=["urban", "rural"],
        )
        assert result == "urban"

    def test_classify_dog(self):
        img = marvin.beta.Image(
            "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg"
        )
        result = marvin.beta.classify(
            img,
            labels=["cat", "dog", "horse"],
        )
        assert result == "dog"

    def test_classify_dog_color(self):
        img = marvin.beta.Image(
            "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg"
        )
        result = marvin.beta.classify(
            img,
            labels=["brown", "black", "blonde", "white", "gray", "golden", "red"],
            instructions="the color of the dog",
        )
        assert result == "white"

    def test_classify_background_color(self):
        img = marvin.beta.Image(
            "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg"
        )
        result = marvin.beta.classify(
            img,
            labels=["brown", "black", "spotted", "white", "green", "blue"],
            instructions="the color of the background",
        )
        assert result == "green"

    def test_classify_wet_dog(self):
        img = marvin.beta.Image(
            "https://upload.wikimedia.org/wikipedia/commons/d/d5/Retriever_in_water.jpg"
        )

        animal = marvin.beta.classify(
            img, labels=["dog", "cat", "bird", "fish", "deer"]
        )
        assert animal == "dog"

        dry_or_wet = marvin.beta.classify(
            img, labels=["dry", "wet"], instructions="Is the animal wet?"
        )
        assert dry_or_wet == "wet"
