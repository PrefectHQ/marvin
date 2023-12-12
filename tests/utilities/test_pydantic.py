import json
from datetime import date, datetime

import pytest
from marvin.utilities.pydantic import parse_as
from pydantic import BaseModel


class ExampleModel(BaseModel):
    name: str


class TestParseAs:
    class TestParseAsPythonMode:
        def test_coerce_to_native_type(self):
            assert parse_as(int, 123, mode="python") == 123

        def test_coerce_to_list_of_native_type(self):
            assert parse_as(list[int], [1, 2, 3], mode="python") == [1, 2, 3]

        def test_coerce_to_base_model(self):
            data = {"name": "Marvin"}
            result = parse_as(ExampleModel, data, mode="python")
            assert isinstance(result, ExampleModel)
            assert result.name == "Marvin"

        def test_coerce_to_list_of_base_model(self):
            data = [{"name": "Marvin"}, {"name": "Arthur"}]
            result = parse_as(list[ExampleModel], data, mode="python")
            assert all(isinstance(item, ExampleModel) for item in result)
            assert result[0].name == "Marvin"
            assert result[1].name == "Arthur"

    class TestParseAsJSONMode:
        def test_coerce_to_native_type(self):
            assert parse_as(int, "123", mode="json") == 123

        def test_coerce_to_list_of_native_type(self):
            assert parse_as(list[int], "[1, 2, 3]", mode="json") == [1, 2, 3]

        def test_coerce_to_base_model(self):
            data = '{"name": "Marvin"}'
            result = parse_as(ExampleModel, data, mode="json")
            assert isinstance(result, ExampleModel)
            assert result.name == "Marvin"

        def test_coerce_to_list_of_base_model(self):
            data = '[{"name": "Marvin"}, {"name": "Arthur"}]'
            result = parse_as(list[ExampleModel], data, mode="json")
            assert all(isinstance(item, ExampleModel) for item in result)
            assert result[0].name == "Marvin"
            assert result[1].name == "Arthur"

    class TestParseAsStringsMode:
        @pytest.mark.parametrize(
            "type_, input_value, expected",
            [
                (bool, "true", True),
                (bool, "false", False),
                (int, "1", 1),
                (float, "1.1", 1.1),
                (date, "2017-01-01", date(2017, 1, 1)),
                (
                    datetime,
                    "2017-01-01T12:13:14.567",
                    datetime(2017, 1, 1, 12, 13, 14, 567_000),
                ),
            ],
        )
        def test_coerce_to_native_types(self, type_, input_value, expected):
            assert parse_as(type_, input_value, mode="strings") == expected

        def test_coerce_to_dict_with_specific_types(self):
            """See https://github.com/pydantic/pydantic/blob/main/tests/test_type_adapter.py#L308"""
            input_dict = json.loads('{"1": "2017-01-01", "2": "2017-01-02"}')
            expected_dict = {
                1: date(2017, 1, 1),
                2: date(2017, 1, 2),
            }
            assert (
                parse_as(dict[int, date], input_dict, mode="strings") == expected_dict
            )
