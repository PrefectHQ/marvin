import pytest

from marvin.utilities.tools import update_fn


def test_update_fn_sync_decorator_positional():
    """Test update_fn as decorator with positional argument"""

    @update_fn("new_name")
    def my_fn(x: int) -> int:
        return x + 1

    assert my_fn.__name__ == "new_name"
    assert my_fn(1) == 2


def test_update_fn_sync_decorator_keyword():
    """Test update_fn as decorator with keyword arguments"""

    @update_fn(name="another_name", description="adds stuff")
    def another_fn(x: int) -> int:
        return x + 2

    assert another_fn.__name__ == "another_name"
    assert another_fn.__doc__ == "adds stuff"
    assert another_fn(1) == 3


def test_update_fn_sync_direct():
    """Test update_fn called directly on a function"""

    def third_fn(x: int) -> int:
        return x + 3

    renamed = update_fn(third_fn, name="third_name")
    assert renamed.__name__ == "third_name"
    assert renamed(1) == 4


async def test_update_fn_async_decorator_positional():
    """Test update_fn as decorator with positional argument on async function"""

    @update_fn("async_name")
    async def my_async_fn(x: int) -> int:
        return x + 1

    assert my_async_fn.__name__ == "async_name"
    assert await my_async_fn(1) == 2


async def test_update_fn_async_decorator_keyword():
    """Test update_fn as decorator with keyword arguments on async function"""

    @update_fn(name="another_async", description="adds stuff async")
    async def another_async_fn(x: int) -> int:
        return x + 2

    assert another_async_fn.__name__ == "another_async"
    assert another_async_fn.__doc__ == "adds stuff async"
    assert await another_async_fn(1) == 3


async def test_update_fn_async_direct():
    """Test update_fn called directly on async function"""

    async def third_async_fn(x: int) -> int:
        return x + 3

    renamed = update_fn(third_async_fn, name="third_async")
    assert renamed.__name__ == "third_async"
    assert await renamed(1) == 4


def test_update_fn_validation_missing_name_direct():
    """Test update_fn validation when name is missing in direct call"""
    with pytest.raises(
        ValueError, match="name must be provided when used as a function"
    ):
        update_fn(lambda x: x)


def test_update_fn_validation_missing_name_decorator():
    """Test update_fn validation when name is missing in decorator"""
    with pytest.raises(
        ValueError, match="name must be provided either as argument or keyword"
    ):

        @update_fn()
        def my_fn(x):
            return x
