import marvin
import pytest


@pytest.fixture(autouse=True)
def use_gpt4o_for_all_tests(gpt_4):
    pass


@pytest.mark.flaky(max_runs=2)
class TestVisionClassify:
    def test_ny(self):
        img = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.classify(img, labels=["urban", "rural"])
        assert result == "urban"

    def test_ny_images_input(self):
        img = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.classify(data=None, images=[img], labels=["urban", "rural"])
        assert result == "urban"

    def test_ny_image_input(self):
        img = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.classify(data=img, labels=["urban", "rural"])
        assert result == "urban"

    def test_ny_image_and_text(self):
        img = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.classify(
            data="I see the empire state building",
            images=[img],
            labels=["urban", "rural"],
        )
        assert result == "urban"

    def test_classify_dog(self):
        img = marvin.Image(
            "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg"
        )
        result = marvin.classify(
            img,
            labels=["cat", "dog", "horse"],
        )
        assert result == "dog"

    def test_classify_dog_color(self):
        img = marvin.Image(
            "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg"
        )
        result = marvin.classify(
            img,
            labels=["brown", "black", "blonde", "white", "gray", "golden", "red"],
            instructions="the color of the dog",
        )
        assert result == "white"

    def test_classify_background_color(self):
        img = marvin.Image(
            "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg"
        )
        result = marvin.classify(
            img,
            labels=["brown", "black", "spotted", "white", "green", "blue"],
            instructions="the color of the background",
        )
        assert result == "green"

    def test_classify_wet_dog(self):
        img = marvin.Image(
            "https://upload.wikimedia.org/wikipedia/commons/d/d5/Retriever_in_water.jpg"
        )

        animal = marvin.classify(img, labels=["dog", "cat", "bird", "fish", "deer"])
        assert animal == "dog"

        dry_or_wet = marvin.classify(
            img, labels=["dry", "wet"], instructions="Is the animal wet?"
        )
        assert dry_or_wet == "wet"


class TestAsync:
    async def test_ny(self):
        img = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = await marvin.classify_async(img, labels=["urban", "rural"])
        assert result == "urban"


class TestReturnIndex:
    def test_return_index(self):
        result = marvin.classify(
            "This is a great feature!", ["bad", "good"], return_index=True
        )
        assert result == 1


class TestMapping:
    def test_map(self):
        ny = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        dc = marvin.Image(
            "https://images.unsplash.com/photo-1617581629397-a72507c3de9e"
        )
        result = marvin.classify.map([ny, dc], labels=["urban", "rural"])
        assert isinstance(result, list)
        assert result == ["urban", "urban"]

    async def test_map_async(self):
        ny = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        dc = marvin.Image(
            "https://images.unsplash.com/photo-1617581629397-a72507c3de9e"
        )
        result = await marvin.classify_async.map([ny, dc], labels=["urban", "rural"])
        assert isinstance(result, list)
        assert result == ["urban", "urban"]
