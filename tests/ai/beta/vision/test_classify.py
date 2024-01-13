import marvin

dog_image = "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg"


class TestVisionClassify:
    def test_classify_dog(self):
        result = marvin.classify_vision(
            images=[dog_image],
            labels=["cat", "dog", "horse"],
        )
        assert result == "dog"

    def test_classify_dog_color(self):
        result = marvin.classify_vision(
            images=[dog_image],
            labels=["brown", "black", "blonde", "white", "gray", "golden", "red"],
            instructions="the color of the dog",
        )
        assert result == "white"

    def test_classify_background_color(self):
        result = marvin.classify_vision(
            images=[dog_image],
            labels=["brown", "black", "spotted", "white", "green", "blue"],
            instructions="the color of the background",
        )
        assert result == "green"

    def test_classify_wet_dog(self):
        img = (
            "https://upload.wikimedia.org/wikipedia/commons/d/d5/Retriever_in_water.jpg"
        )

        animal = marvin.classify_vision(
            img, labels=["dog", "cat", "bird", "fish", "deer"]
        )
        assert animal == "dog"

        dry_or_wet = marvin.classify_vision(
            img, labels=["dry", "wet"], instructions="Is the animal wet?"
        )
        assert dry_or_wet == "wet"
