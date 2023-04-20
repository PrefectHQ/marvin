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


class TestContextAwareFillna:
    def test_fill_states(self):
        result = data_fns.context_aware_fillna(
            data=[
                ["New York", None],
                ["Boston", "MA"],
                ["Los Angeles", None],
            ],
            columns=["city", "state"],
        )
        assert result == [
            ["New York", "NY"],
            ["Boston", "MA"],
            ["Los Angeles", "CA"],
        ]

    def test_fill_movies(self):
        data = [
            ["The Terminator", 1984, None],
            ["Minority Report", None, "Steven Spielberg"],
            ["WALL-E", None, "Andrew Stanton"],
            ["Blade Runner", 1982, None],
        ]
        result = data_fns.context_aware_fillna(
            data, columns=["title", "release_year", "director"]
        )
        assert result == [
            ["The Terminator", 1984, "James Cameron"],
            ["Minority Report", 2002, "Steven Spielberg"],
            ["WALL-E", 2008, "Andrew Stanton"],
            ["Blade Runner", 1982, "Ridley Scott"],
        ]
