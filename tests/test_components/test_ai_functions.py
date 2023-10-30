import inspect
from typing import Dict, List

import pytest
from marvin import ai_fn
from pydantic import BaseModel

from tests.utils.mark import pytest_mark_class


@ai_fn
def list_fruit(n: int = 2) -> list[str]:
    """Returns a list of `n` fruit"""


@ai_fn
def list_fruit_color(n: int, color: str = None) -> list[str]:
    """Returns a list of `n` fruit that all have the provided `color`"""


@pytest_mark_class("llm")
class TestAIFunctions:
    def test_list_fruit(self):
        result = list_fruit()
        assert len(result) == 2

    def test_list_fruit_argument(self):
        result = list_fruit(5)
        assert len(result) == 5

    async def test_list_fruit_async(self):
        @ai_fn
        async def list_fruit(n: int) -> list[str]:
            """Returns a list of `n` fruit"""

        coro = list_fruit(3)
        assert inspect.iscoroutine(coro)
        result = await coro
        assert len(result) == 3

    def test_list_fruit_with_generic_type_hints(self):
        @ai_fn
        def list_fruit(n: int) -> List[str]:
            """Returns a list of `n` fruit"""

        result = list_fruit(3)
        assert len(result) == 3

    def test_basemodel_return_annotation(self):
        class Fruit(BaseModel):
            name: str
            color: str

        @ai_fn
        def get_fruit(description: str) -> Fruit:
            """Returns a fruit with the provided description"""

        fruit = get_fruit("loved by monkeys")
        assert fruit.name.lower() == "banana"
        assert fruit.color.lower() == "yellow"

    @pytest.mark.parametrize("name,expected", [("banana", True), ("car", False)])
    def test_bool_return_annotation(self, name, expected):
        @ai_fn
        def is_fruit(name: str) -> bool:
            """Returns True if the provided name is a fruit"""

        assert is_fruit(name) == expected

    def test_plain_dict_return_type(self):
        @ai_fn
        def get_fruit(name: str) -> dict:
            """Returns a fruit with the provided name and color"""

        fruit = get_fruit("banana")
        assert fruit["name"].lower() == "banana"
        assert fruit["color"].lower() == "yellow"

    def test_annotated_dict_return_type(self):
        @ai_fn
        def get_fruit(name: str) -> dict[str, str]:
            """Returns a fruit with the provided name and color"""

        fruit = get_fruit("banana")
        assert fruit["name"].lower() == "banana"
        assert fruit["color"].lower() == "yellow"

    def test_generic_dict_return_type(self):
        @ai_fn
        def get_fruit(name: str) -> Dict[str, str]:
            """Returns a fruit with the provided name and color"""

        fruit = get_fruit("banana")
        assert fruit["name"].lower() == "banana"
        assert fruit["color"].lower() == "yellow"

    def test_int_return_type(self):
        @ai_fn
        def get_fruit(name: str) -> int:
            """Returns the number of letters in the provided fruit name"""

        assert get_fruit("banana") == 6

    def test_float_return_type(self):
        @ai_fn
        def get_fruit(name: str) -> float:
            """Returns the number of letters in the provided fruit name"""

        assert get_fruit("banana") == 6.0

    def test_tuple_return_type(self):
        @ai_fn
        def get_fruit(name: str) -> tuple:
            """Returns the number of letters in the provided fruit name"""

        assert get_fruit("banana") == (6,)

    def test_set_return_type(self):
        @ai_fn
        def get_fruit(name: str) -> set:
            """Returns the letters in the provided fruit name"""

        assert get_fruit("banana") == {"a", "b", "n"}

    def test_frozenset_return_type(self):
        @ai_fn
        def get_fruit(name: str) -> frozenset:
            """Returns the letters in the provided fruit name"""

        assert get_fruit("banana") == frozenset({"a", "b", "n"})


@pytest_mark_class("llm")
class TestAIFunctionsMap:
    def test_map(self):
        result = list_fruit_color.map([2, 3])
        assert len(result) == 2
        assert len(result[0]) == 2
        assert len(result[1]) == 3

    async def test_amap(self):
        result = await list_fruit_color.amap([2, 3])
        assert len(result) == 2
        assert len(result[0]) == 2
        assert len(result[1]) == 3

    def test_map_kwargs(self):
        result = list_fruit_color.map(n=[2, 3])
        assert len(result) == 2
        assert len(result[0]) == 2
        assert len(result[1]) == 3

    def test_map_kwargs_and_args(self):
        result = list_fruit_color.map([2, 3], color=[None, "red"])
        assert len(result) == 2
        assert len(result[0]) == 2
        assert len(result[1]) == 3

    def test_invalid_args(self):
        with pytest.raises(TypeError):
            list_fruit_color.map(2, color=["orange", "red"])

    def test_invalid_kwargs(self):
        with pytest.raises(TypeError):
            list_fruit_color.map([2, 3], color=None)

    async def test_invalid_async_map(self):
        with pytest.raises(TypeError, match="can't be used in 'await' expression"):
            await list_fruit_color.map(n=[2], color=["orange", "red"])
