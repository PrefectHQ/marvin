from marvin.ai_functions import data as data_fns


class TestCategorizeData:
    def test_categorize_airports_to_cities(self):
        result = data_fns.categorize_data(
            ["LGA", "DCA", "JFK", "BOS"],
            "cities (New York, etc.)",
        )

        assert result == ["New York", "Washington D.C.", "New York", "Boston"]

    def test_categorize_colors(self):
        result = data_fns.categorize_data(
            ["red", "teal", "sunflower", "cyan"],
            "colors of the rainbow",
        )
        assert result == ["red", "blue", "yellow", "blue"]


class TestCategorizeDataExact:
    def test_categorize_plant_to_fruit_or_vegetable(self):
        result = data_fns.categorize_data_exact(
            data=["apple", "carrot", "banana", "broccoli"],
            categories=["fruit", "vegetable"],
        )

        assert result == ["fruit", "vegetable", "fruit", "vegetable"]

    def test_categorize_colors(self):
        result = data_fns.categorize_data_exact(
            data=["red", "yellow", "orange", "cyan"], categories=["red", "blue"]
        )
        assert result == ["red", "red", "red", "blue"]
