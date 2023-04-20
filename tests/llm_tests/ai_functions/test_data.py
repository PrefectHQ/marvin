from marvin.ai_functions import data as data_fns


class TestCategorizeData:
    def test_categorize_airports_to_cities(self):
        result = data_fns.categorize_data(
            ["LGA", "DCA", "JFK", "BOS"],
            category_description="cities (New York, etc.)",
        )

        assert result == ["New York", "Washington D.C.", "New York", "Boston"]

    def test_categorize_colors(self):
        result = data_fns.categorize_data(
            ["red", "teal", "sunflower", "cyan"],
            category_description="colors of the rainbow",
        )
        assert result == ["red", "blue", "yellow", "blue"]

    def test_categorize_bool(self):
        result = data_fns.categorize_data(
            data=["y", "true", "yes", "n", "T"], category_description="true or false"
        )

        assert result == ["true", "true", "true", "false", "true"]


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

    def test_categorize_bool(self):
        result = data_fns.categorize_data_exact(
            data=["y", "true", "yes", "n", "T"], categories=["true", "false"]
        )

        assert result == ["true", "true", "true", "false", "true"]


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


class TestStandardize:
    def test_standardize_phone_numbers(self):
        result = data_fns.standardize(
            data=["(555) 555.5555", "555-555-5555", "5555555555", "123.456.7890"],
            format="US phone number with area code",
        )
        assert result == [
            "(555) 555-5555",
            "(555) 555-5555",
            "(555) 555-5555",
            "(123) 456-7890",
        ]

    def test_standardize_true_false(self):
        result = data_fns.standardize(
            data=["y", "true", "yes", "n", "T", "N"],
            format="true or false",
        )
        assert result == ["true", "true", "true", "false", "true", "false"]

    def test_standardize_zip_code(self):
        result = data_fns.standardize(
            data=["1994-04-14", "3/30/1985", "4/24/19", "15 apr 2010"],
            format="M/D/YYYY",
        )
        assert result == ["4/14/1994", "3/30/1985", "4/24/2019", "4/15/2010"]
