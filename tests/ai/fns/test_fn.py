import inspect
from enum import Enum
from typing import Literal

import pytest
from pydantic import BaseModel

import marvin
from marvin.utilities.testing import assert_llm_equal


@marvin.fn
def list_fruit(n: int = 2) -> list[str]:
    """Returns a list of `n` fruit"""


@marvin.fn
def list_fruit_color(n: int, color: str | None = None) -> list[str]:
    """Returns a list of `n` fruit that all have the provided `color`"""


class TestBasics:
    def test_list_fruit(self):
        result = list_fruit()
        assert len(result) == 2

    def test_list_fruit_argument(self):
        result = list_fruit(5)
        assert len(result) == 5


class TestAnnotations:
    def test_no_annotations(self):
        @marvin.fn
        def f(x):
            """Returns x + 1"""

        result = f(3)
        assert result == 4

    @pytest.mark.flaky(reruns=3)
    def test_arg_annotations(self):
        @marvin.fn
        def f(x: int):
            """Returns x + 1"""

        result = f(3)
        assert result == 4

    @pytest.mark.flaky(reruns=3)
    @pytest.mark.usefixtures("gpt_4o")
    def test_no_annotation_attempts_to_load_as_json_gracefully(self):
        # the trailing comma will fail to load as json, so we should
        # gracefully fall back to the string
        @marvin.fn
        def f(x):
            """Returns the value (x + 1) with a trailing comma

            For example, f(8) -> '9,'  f(100) -> '101,'"""

        result = f("3")
        assert result == "4,"

    def test_return_annotations(self):
        @marvin.fn
        def f(x) -> int:
            """Returns x + 1"""

        result = f("3")
        assert result == 4

    def test_list_fruit_with_generic_type_hints(self):
        @marvin.fn
        def list_fruit(n: int) -> list[str]:
            """Returns a list of `n` fruit"""

        result = list_fruit(3)
        assert len(result) == 3

    def test_basemodel_return_annotation(self):
        class Fruit(BaseModel):
            name: str
            color: str

        @marvin.fn
        def get_fruit(description: str) -> Fruit:
            """Returns a fruit with the provided description"""

        fruit = get_fruit("loved by monkeys")
        assert fruit.name.lower() == "banana"
        assert fruit.color.lower() == "yellow"

    @pytest.mark.parametrize("name,expected", [("banana", True), ("car", False)])
    def test_bool_return_annotation(self, name: str, expected: bool):
        @marvin.fn
        def is_fruit(name: str) -> bool:
            """Returns True if the provided name is a fruit"""

        assert is_fruit(name) == expected

    @pytest.mark.flaky(reruns=2)
    def test_plain_dict_return_type(self):
        @marvin.fn
        def describe_fruit(description: str) -> dict:
            """Guess the fruit and return a dict with `name` and `color` as keys"""

        fruit = describe_fruit("the one thats loved by monkeys")
        assert fruit["name"].lower() == "banana"
        assert fruit["color"].lower() == "yellow"

    @pytest.mark.flaky(reruns=2)
    def test_annotated_dict_return_type(self):
        @marvin.fn
        def describe_fruit(description: str) -> dict[str, str]:
            """Guess the fruit and return a dict with `name` and `color` as keys"""

        fruit = describe_fruit("the one thats loved by monkeys")
        assert fruit["name"].lower() == "banana"
        assert fruit["color"].lower() == "yellow"

    def test_typed_dict_return_type(self):
        from typing_extensions import TypedDict

        class Fruit(TypedDict):
            name: str
            color: str

        @marvin.fn
        def describe_fruit(description: str) -> Fruit:
            """Guess the fruit and return the name and color as keys"""

        fruit = describe_fruit("the one thats loved by monkeys")
        assert fruit["name"].lower() == "banana"
        assert fruit["color"].lower() == "yellow"

    def test_int_return_type(self):
        @marvin.fn
        def get_fruit(name: str) -> int:
            """Returns the number of letters in the alluded fruit name"""

        assert get_fruit("banana") == 6

    def test_float_return_type(self):
        @marvin.fn
        def get_pi(n: int) -> float:
            """Return the first n decimals of pi"""

        assert get_pi(5) == 3.14159

    @pytest.mark.flaky(reruns=3)
    @pytest.mark.xfail(
        reason="pydantic-ai 0.6.x generates invalid schema for untyped tuple"
    )
    def test_tuple_return_type(self):
        @marvin.fn
        def get_fruit(name: str) -> tuple:
            """Returns a tuple of fruit"""

        result = get_fruit("alphabet of fruit, first 3, singular")
        assert isinstance(result, tuple)

        # sometimes gpt-4o-mini returns a tuple of dicts
        assert result == ("apple", "banana", "cherry") or (
            "apple" in str(result)
            and "banana" in str(result)
            and "cherry" in str(result)
        )

    # fails due to incompatibiliy with OpenAPI schemas and OpenAI
    @pytest.mark.xfail(reason="OpenAPI schemas don't support typed tuples?")
    def test_typed_tuple_return_type(self):
        @marvin.fn
        def get_letter_index(letter: str) -> tuple[str, int]:
            """Returns a tuple of the provided letter and its position in the
            alphabet. For example, a -> (a, 1); b -> (b, 2); etc.
            """

        assert get_letter_index("d") == ("d", 4)

    @pytest.mark.xfail(
        reason="https://github.com/pydantic/pydantic/issues/11360 requires pydantic-core >= 2.30"
    )
    def test_set_return_type(self):
        @marvin.fn
        def get_fruit_letters(name: str) -> set:
            """Returns only the unique letters in the provided fruit name"""

        assert get_fruit_letters("banana") == {"a", "b", "n"}

    @pytest.mark.xfail(
        reason="https://github.com/pydantic/pydantic/issues/11360 requires pydantic-core >= 2.30"
    )
    def test_frozenset_return_type(self):
        """Use GPT-4o"""

        @marvin.fn
        def get_fruit_letters(name: str) -> frozenset:
            """
            Returns a list of the letters in the provided fruit name.

            Your response should just be a list of letters, not dicts: ['h', 'e', 'l', 'l', 'o']

            """

        assert get_fruit_letters("orange") == frozenset(
            {"a", "e", "g", "n", "o", "r"},
        )

    def test_enum_return_type(self):
        class Fruit(Enum):
            # fruits of different colors
            APPLE = "APPLE"
            BANANA = "BANANA"
            ORANGE = "ORANGE"
            BLUEBERRY = "BLUEBERRY"

        @marvin.fn
        def get_fruit(color: str) -> Fruit:
            """Returns the fruit with the provided color"""

        assert get_fruit("yellow") == Fruit.BANANA

    def test_literal_return_type(self):
        @marvin.fn
        def get_fruit(
            color: str,
        ) -> Literal["APPLE", "BANANA", "ORANGE", "BLUEBERRY"]:
            """Returns the fruit that matches the provided color"""

        assert get_fruit("yellow") == "BANANA"

    def test_list_instance_return_type(self):
        @marvin.fn
        def get_fruit(
            color: str,
        ) -> ["APPLE", "BANANA", "ORANGE", "BLUEBERRY"]:  # noqa F821
            """Returns the fruit that matches the provided color"""

        assert get_fruit("yellow") == "BANANA"


class TestAsync:
    async def test_decorated_async_function(self):
        @marvin.fn
        async def list_fruit(n: int) -> list[str]:
            """Returns a list of `n` fruit"""

        coro = list_fruit(3)
        assert inspect.iscoroutine(coro)

        result = await coro
        assert len(result) == 3


class TestAsTask:
    def test_as_task_method(self):
        @marvin.fn
        def list_fruit(n: int) -> list[str]:
            """Returns a list of `n` fruit"""

        task = list_fruit.as_task(3)
        assert isinstance(task, marvin.Task)
        assert task.result_type == list[str]
        assert task.name == "Predict output of list_fruit"
        assert "Function definition" in task.context
        assert task.context["Function arguments"] == {"n": 3}

    def test_as_task_with_instructions(self):
        @marvin.fn(instructions="Only return citrus fruits")
        def list_fruit(n: int) -> list[str]:
            """Returns a list of `n` fruit"""

        task = list_fruit.as_task(3, _instructions="Only return tropical fruits")
        assert isinstance(task, marvin.Task)
        assert task.context["Additional instructions"] == "Only return tropical fruits"


class TestContextAndInstructions:
    async def test_fn_with_instructions(self):
        @marvin.fn(instructions="Only return citrus fruits")
        def list_fruit(n: int) -> list[str]:
            """Returns a list of `n` fruit"""

        result = list_fruit(3)
        await assert_llm_equal(result, "a list of three citrus fruits")
        assert len(result) == 3

    def test_fn_with_return_value_context(self):
        @marvin.fn
        def get_fruit(name_or_description: str) -> str:
            """Return the name of a fruit"""
            return {"hint": "This fruit is yellow and curved"}

        result = get_fruit("?????its such a mystery??????")
        assert result.lower() == "banana"

    async def test_async_fn_with_instructions(self):
        @marvin.fn(instructions="Only return berries")
        async def list_fruit(n: int) -> list[str]:
            """Returns a list of `n` fruit"""

        result = await list_fruit(3)
        await assert_llm_equal(result, "a list of three berries")
        assert len(result) == 3

    @pytest.mark.xfail(reason="This is a flaky test that should be fixed")
    async def test_async_fn_with_return_value_context(self):
        @marvin.fn
        async def get_fruit_details(name: str) -> dict[str, str]:
            """Returns details about the fruit"""
            return {"hint": "we talkin apples yo"}

        result = await get_fruit_details("unknown")
        await assert_llm_equal(result, "a dictionary describing an apple")

    @pytest.mark.xfail(reason="This is a flaky test that should be fixed")
    async def test_fn_with_instructions_and_context(self):
        @marvin.fn(instructions="Only return tropical fruits")
        def get_fruit_details(name: str) -> dict[str, str]:
            """Returns details about the fruit"""
            return {"hint if unknown": "its a coconut"}

        result = get_fruit_details("unknown")
        await assert_llm_equal(result, "a dictionary describing a coconut")

    @pytest.mark.xfail(reason="This is a flaky test that should be fixed")
    async def test_async_fn_with_instructions_and_context(self):
        @marvin.fn(instructions="Only consider fruits from Asia")
        async def get_fruit_details(name: str) -> dict[str, str]:
            """Returns details about the fruit"""
            return {"hint": "This fruit has spikes on the outside"}

        result = await get_fruit_details("unknown")
        await assert_llm_equal(result, "a dictionary describing a durian")

    async def test_fn_with_runtime_instructions(self):
        @marvin.fn
        def list_fruit(n: int) -> list[str]:
            """Returns a list of `n` fruit"""

        result = list_fruit(3, _instructions="Only return red fruits")
        await assert_llm_equal(result, "a list of three red fruits")
        assert len(result) == 3

    async def test_async_fn_with_runtime_instructions(self):
        @marvin.fn
        async def list_fruit(n: int) -> list[str]:
            """Returns a list of `n` fruit"""

        result = await list_fruit(3, _instructions="Only return yellow fruits")
        await assert_llm_equal(result, "a list of three yellow fruits")
        assert len(result) == 3
