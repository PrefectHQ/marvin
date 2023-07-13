import inspect

import pytest
from marvin import ai_fn

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


@pytest_mark_class("llm")
class TestAIFunctionsMap:
    def test_map(self):
        result = list_fruit_color.map([2, 3])
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
