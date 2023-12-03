import inspect
from typing import Dict, List

import marvin
import pytest
from marvin import ai_fn
from pydantic import BaseModel

from tests.utils import pytest_mark_class


@ai_fn
def list_fruit(n: int = 2) -> list[str]:
    """Returns a list of `n` fruit"""


@ai_fn
def list_fruit_color(n: int, color: str = None) -> list[str]:
    """Returns a list of `n` fruit that all have the provided `color`"""


@pytest_mark_class("llm")
class TestAIFunctions:
    class TestBasics:
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

    class TestAnnotations:
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

        @pytest.mark.skipif(
            marvin.settings.openai.chat.completions.model == "gpt-3.5-turbo-1106",
            reason="3.5 turbo doesn't do well with unknown schemas",
        )
        def test_plain_dict_return_type(self):
            @ai_fn
            def describe_fruit(description: str) -> dict:
                """guess the fruit and return the name and color"""

            fruit = describe_fruit("the one thats loved by monkeys")
            assert fruit["name"].lower() == "banana"
            assert fruit["color"].lower() == "yellow"

        @pytest.mark.skipif(
            marvin.settings.openai.chat.completions.model == "gpt-3.5-turbo-1106",
            reason="3.5 turbo doesn't do well with unknown schemas",
        )
        def test_annotated_dict_return_type(self):
            @ai_fn
            def describe_fruit(description: str) -> dict[str, str]:
                """guess the fruit and return the name and color"""

            fruit = describe_fruit("the one thats loved by monkeys")
            assert fruit["name"].lower() == "banana"
            assert fruit["color"].lower() == "yellow"

        @pytest.mark.skipif(
            marvin.settings.openai.chat.completions.model == "gpt-3.5-turbo-1106",
            reason="3.5 turbo doesn't do well with unknown schemas",
        )
        def test_generic_dict_return_type(self):
            @ai_fn
            def describe_fruit(description: str) -> Dict[str, str]:
                """guess the fruit and return the name and color"""

            fruit = describe_fruit("the one thats loved by monkeys")
            assert fruit["name"].lower() == "banana"
            assert fruit["color"].lower() == "yellow"

        def test_typed_dict_return_type(self):
            from typing_extensions import TypedDict

            class Fruit(TypedDict):
                name: str
                color: str

            @ai_fn
            def describe_fruit(description: str) -> Fruit:
                """guess the fruit and return the name and color"""

            fruit = describe_fruit("the one thats loved by monkeys")
            assert fruit["name"].lower() == "banana"
            assert fruit["color"].lower() == "yellow"

        def test_int_return_type(self):
            @ai_fn
            def get_fruit(name: str) -> int:
                """Returns the number of letters in the alluded fruit name"""

            assert get_fruit("banana") == 6

        def test_float_return_type(self):
            @ai_fn
            def get_pi(n: int) -> float:
                """Return the first n digits of pi"""

            assert get_pi(5) == 3.14159

        def test_tuple_return_type(self):
            @ai_fn
            def get_fruit(name: str) -> tuple:
                """Returns a tuple of fruit"""

            assert get_fruit("alphabet of fruit, first 3") == (
                "apple",
                "banana",
                "cherry",
            )

        def test_set_return_type(self):
            @ai_fn
            def get_fruit_letters(name: str) -> set:
                """Returns the letters in the provided fruit name"""

            assert get_fruit_letters("banana") == {"a", "b", "n"}

        def test_frozenset_return_type(self):
            @ai_fn
            def get_fruit_letters(name: str) -> frozenset:
                """Returns the letters in the provided fruit name"""

            assert get_fruit_letters("orange") == frozenset(
                {"a", "e", "g", "n", "o", "r"}
            )


@pytest_mark_class("llm")
class TestAIFunctionsMap:
    def test_map(self):
        result = list_fruit.map([2, 3])
        assert len(result) == 2
        assert len(result[0]) == 2
        assert len(result[1]) == 3

    async def test_amap(self):
        result = await list_fruit.amap([2, 3])
        assert len(result) == 2
        assert len(result[0]) == 2
        assert len(result[1]) == 3

    def test_map_kwargs(self):
        result = list_fruit.map(n=[2, 3])
        assert len(result) == 2
        assert len(result[0]) == 2
        assert len(result[1]) == 3

    def test_map_kwargs_and_args(self):
        result = list_fruit_color.map([2, 3], color=["green", "red"])
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
