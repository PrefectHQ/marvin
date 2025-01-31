import pytest

from marvin.utilities.tools import update_fn


class TestUpdateFnCalled:
    """Tests for update_fn when used as a direct function call"""

    def test_name(self):
        """Test update_fn as direct function call with name argument"""

        def my_fn(x: int) -> int:
            return x + 1

        updated = update_fn(my_fn, name="new_name")
        assert updated.__name__ == "new_name"
        assert updated(1) == 2

    def test_name_and_description(self):
        """Test update_fn as direct function call with name and description"""

        def my_fn(x: int) -> int:
            return x + 1

        updated = update_fn(my_fn, name="new_name", description="adds stuff")
        assert updated.__name__ == "new_name"
        assert updated.__doc__ == "adds stuff"
        assert updated(1) == 2

    async def test_async(self):
        """Test update_fn as direct function call with async function"""

        async def my_async_fn(x: int) -> int:
            return x + 1

        updated = update_fn(my_async_fn, name="new_async_name")
        assert updated.__name__ == "new_async_name"
        assert await updated(1) == 2

    def test_preserves_docstring(self):
        """Test that original docstring is preserved in direct call when no description provided"""

        def my_fn(x: int) -> int:
            """Original docstring"""
            return x + 1

        updated = update_fn(my_fn, name="new_name")
        assert updated.__doc__ == "Original docstring"

    def test_preserves_name(self):
        """Test that original name is preserved in direct call when no name provided"""

        def original_name_fn(x: int) -> int:
            return x + 1

        updated = update_fn(original_name_fn, description="new description")
        assert updated.__name__ == "original_name_fn"


class TestUpdateFnDecorator:
    """Tests for update_fn when used as a decorator"""

    def test_name(self):
        """Test update_fn as decorator with name argument"""

        @update_fn(name="new_name")
        def my_fn(x: int) -> int:
            return x + 1

        assert my_fn.__name__ == "new_name"
        assert my_fn(1) == 2

    def test_name_and_description(self):
        """Test update_fn as decorator with name and description"""

        @update_fn(name="another_name", description="adds stuff")
        def another_fn(x: int) -> int:
            return x + 2

        assert another_fn.__name__ == "another_name"
        assert another_fn.__doc__ == "adds stuff"
        assert another_fn(1) == 3

    def test_no_args(self):
        """Test update_fn as decorator with no arguments"""

        @update_fn()
        def third_fn(x: int) -> int:
            return x + 3

        assert third_fn(1) == 4

    async def test_async_name(self):
        """Test update_fn as decorator with name argument on async function"""

        @update_fn(name="async_name")
        async def my_async_fn(x: int) -> int:
            return x + 1

        assert my_async_fn.__name__ == "async_name"
        assert await my_async_fn(1) == 2

    async def test_async_name_and_description(self):
        """Test update_fn as decorator with name and description on async function"""

        @update_fn(name="another_async", description="adds stuff async")
        async def another_async_fn(x: int) -> int:
            return x + 2

        assert another_async_fn.__name__ == "another_async"
        assert another_async_fn.__doc__ == "adds stuff async"
        assert await another_async_fn(1) == 3

    def test_description_only(self):
        """Test update_fn as decorator with only description"""

        @update_fn(description="only description")
        def my_fn(x: int) -> int:
            return x + 1

        assert my_fn.__doc__ == "only description"
        assert my_fn(1) == 2

    def test_preserves_original_name(self):
        """Test that original function name is preserved when no name provided"""

        @update_fn(description="some description")
        def original_name_fn(x: int) -> int:
            return x + 1

        assert original_name_fn.__name__ == "original_name_fn"

    def test_preserves_original_docstring(self):
        """Test that original docstring is preserved when no description provided"""

        @update_fn(name="new_name")
        def my_fn(x: int) -> int:
            """Original docstring"""
            return x + 1

        assert my_fn.__doc__ == "Original docstring"

    def test_preserves_all_original(self):
        """Test that both original name and docstring are preserved with empty decorator"""

        @update_fn()
        def preserve_me(x: int) -> int:
            """Keep this docstring"""
            return x + 1

        assert preserve_me.__name__ == "preserve_me"
        assert preserve_me.__doc__ == "Keep this docstring"

    def test_empty_description_allowed(self):
        """Test that empty description is allowed"""

        @update_fn(name="new_name", description="")
        def my_fn(x: int) -> int:
            """Original doc"""
            return x + 1

        assert my_fn.__name__ == "new_name"
        assert my_fn.__doc__ == ""

    def test_empty_name_not_allowed(self):
        """Test that empty name is not allowed"""
        with pytest.raises(ValueError, match="name cannot be empty if provided"):

            @update_fn(name="")
            def my_fn(x: int) -> int:
                return x + 1
