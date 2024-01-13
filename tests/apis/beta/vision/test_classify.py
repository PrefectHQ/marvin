import marvin

dog_image = "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg"


class TestVisionClassify:
    def test_classify_dog(self):
        result = marvin.ai.beta.vision.classify(
            images=[dog_image],
            labels=["cat", "dog", "horse"],
        )
        assert result == "dog"

    def test_classify_dog_color(self):
        result = marvin.ai.beta.vision.classify(
            images=[dog_image],
            labels=["brown", "black", "blonde", "white", "gray", "golden", "red"],
            instructions="the color of the dog",
        )
        assert result == "white"

    def test_classify_background_color(self):
        result = marvin.ai.beta.vision.classify(
            images=[dog_image],
            labels=["brown", "black", "spotted", "white", "green", "blue"],
            instructions="the color of the background",
        )
        assert result == "green"
