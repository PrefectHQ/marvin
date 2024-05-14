import marvin
import pytest
from marvin.utilities.testing import assert_equal


@pytest.fixture(autouse=True)
def use_gpt4o_for_all_tests(gpt_4):
    pass


@pytest.mark.flaky(max_runs=2)
class TestVisionCaption:
    def test_ny(self):
        img = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        result = marvin.caption(img, instructions="what city is this?")
        assert_equal(
            result,
            "New York City",
            instructions="A caption was generated. Ensure it mentions the city.",
        )

    def test_dc(self):
        img = marvin.Image(
            "https://images.unsplash.com/photo-1617581629397-a72507c3de9e"
        )
        result = marvin.caption(img, instructions="what city is this?")
        assert_equal(
            result,
            "Washington DC",
            instructions="A caption was generated. Ensure it mentions the city.",
        )

    def test_two_cities(self):
        img_ny = marvin.Image(
            "https://images.unsplash.com/photo-1568515387631-8b650bbcdb90"
        )
        img_dc = marvin.Image(
            "https://images.unsplash.com/photo-1617581629397-a72507c3de9e"
        )

        result = marvin.caption([img_ny, img_dc], instructions="what city is this?")

        assert_equal(
            result,
            "New York City; Washington DC",
            instructions="A caption was generated for two images. Ensure it mentions both cities.",
        )
