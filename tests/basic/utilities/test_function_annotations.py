from __future__ import annotations

import inspect
from typing import Annotated

import pytest
from pydantic import BaseModel, Field, ValidationError

import marvin
from marvin.utilities.types import PythonFunction


class Recipe(BaseModel):
    name: str
    minutes: int


@marvin.fn
def recipe(ingredient: str) -> Recipe:
    """Create a recipe using {{ ingredient }}."""
    return None


@marvin.fn
async def recipe_async(ingredient: str) -> Recipe:
    """Create a recipe using {{ ingredient }}."""
    return None


@pytest.mark.parametrize("function", [recipe, recipe_async])
def test_fn_task_resolves_postponed_model_annotation(function):
    task = function.as_task("rice")
    assert task.result_type is Recipe
    result = task.validate_result({"name": "Risotto", "minutes": 30})
    assert isinstance(result, Recipe)
    assert result.minutes == 30


def test_fn_task_preserves_annotated_constraints():
    @marvin.fn
    def positive_count() -> Annotated[int, Field(gt=0)]:
        """Return a positive count."""
        return None

    task = positive_count.as_task()
    assert task.validate_result(2) == 2
    with pytest.raises(ValidationError):
        task.validate_result(0)


def test_function_without_annotation_keeps_empty_annotation():
    def untyped():
        return "context"

    assert (
        PythonFunction.from_function(untyped).return_annotation
        is inspect.Signature.empty
    )


def test_function_with_unresolved_annotation_keeps_annotation():
    def unresolved():
        return None

    unresolved.__annotations__["return"] = "MissingModel"
    assert PythonFunction.from_function(unresolved).return_annotation == "MissingModel"
