"""Tests for PythonFunction with `from __future__ import annotations`.

This module uses `from __future__ import annotations` to trigger PEP 563 behavior
where all annotations become strings by default.
"""

from __future__ import annotations

import inspect

from pydantic import BaseModel

from marvin.utilities.types import PythonFunction


class Recipe(BaseModel):
    """A recipe model for testing."""

    name: str
    cook_time_minutes: int
    ingredients: list[str]


def recipe_function(ingredients: list[str], max_cook_time: int = 15) -> Recipe:
    """Returns a recipe that uses the provided ingredients."""
    pass


class TestPythonFunctionWithFutureAnnotations:
    """Test that PythonFunction properly resolves annotations with PEP 563."""

    def test_return_annotation_is_resolved_not_string(self):
        """Test that return annotation is the actual type, not a string."""
        model = PythonFunction.from_function(recipe_function)

        # The return annotation should be the actual Recipe class, not a string
        assert model.return_annotation is Recipe
        assert not isinstance(model.return_annotation, str)

    def test_return_annotation_with_builtin_types(self):
        """Test that builtin type annotations are also properly resolved."""

        def func_with_list_return() -> list[int]:
            pass

        model = PythonFunction.from_function(func_with_list_return)

        # Should be a proper generic type, not a string
        assert model.return_annotation is not inspect.Signature.empty
        assert not isinstance(model.return_annotation, str)

    def test_from_function_call_resolves_annotation(self):
        """Test that from_function_call also properly resolves annotations."""

        def simple_func(x: int) -> str:
            return "hello"

        model = PythonFunction.from_function_call(simple_func, 42)

        # Return annotation should be str, not 'str'
        assert model.return_annotation is str
        assert not isinstance(model.return_annotation, str)
