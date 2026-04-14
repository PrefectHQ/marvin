import enum
import inspect
from typing import Literal

import pytest
from pydantic import BaseModel

from marvin.utilities.types import (
    Labels,
    PythonFunction,
    as_classifier,
    is_classifier,
)
from tests.basic.utilities._future_annotations_helper import (
    FutureModel,
    build_future_model,
)


class Colors(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class TestClassification:
    def test_is_classifier_with_raw_types(self):
        """Test classifier detection with raw types."""
        # Raw collections
        assert is_classifier(["alpha", "beta", "gamma"])  # single-label
        assert is_classifier([["alpha", "beta", "gamma"]])  # multi-label shorthand

        # Non-classifiers
        assert not is_classifier(42)  # Number
        assert not is_classifier("string")  # String
        assert not is_classifier(list[str])  # List of any strings

    def test_is_classifier_with_type_hints(self):
        """Test classifier detection with type hints."""
        # Enum types
        assert is_classifier(Colors)
        assert is_classifier(list[Colors])

        # Literal types
        assert is_classifier(Literal["alpha", "beta"])
        assert is_classifier(list[Literal["alpha", "beta"]])

        # Labels
        assert is_classifier(Labels(["alpha", "beta"]))
        assert is_classifier(Labels(["alpha", "beta"], many=True))

        # Non-classifier types
        assert not is_classifier(str)
        assert not is_classifier(list[str])
        assert not is_classifier(list[int])
        assert not is_classifier(dict[str, int])

    def test_as_classifier_with_raw_types(self):
        """Test converting raw types to Labels."""
        # Single-label
        labels = as_classifier(["red", "green", "blue"])
        assert isinstance(labels, Labels)
        assert not labels.many
        assert labels.labels == ("red", "green", "blue")

        # Multi-label shorthand
        labels = as_classifier([["red", "green", "blue"]])
        assert isinstance(labels, Labels)
        assert labels.many
        assert labels.labels == ("red", "green", "blue")

    def test_as_classifier_with_type_hints(self):
        """Test converting type hints to Labels."""
        # Enum types
        labels = as_classifier(Colors)
        assert isinstance(labels, Labels)
        assert not labels.many
        assert [x.value for x in labels.labels] == ["red", "green", "blue"]

        # Multi-label enum
        labels = as_classifier(list[Colors])
        assert isinstance(labels, Labels)
        assert labels.many
        assert [x.value for x in labels.labels] == ["red", "green", "blue"]

        # Literal types
        labels = as_classifier(Literal["alpha", "beta"])
        assert isinstance(labels, Labels)
        assert not labels.many
        assert labels.labels == ("alpha", "beta")

        # Multi-label literal
        labels = as_classifier(list[Literal["alpha", "beta"]])
        assert isinstance(labels, Labels)
        assert labels.many
        assert labels.labels == ("alpha", "beta")

    def test_labels_validation(self):
        """Test validation of Labels."""
        # Single-label
        labels = Labels(["red", "green", "blue"])
        assert labels.validate(0) == "red"
        assert labels.validate(1) == "green"
        with pytest.raises(ValueError):
            labels.validate(3)  # Out of range
        with pytest.raises(ValueError):
            labels.validate([0])  # Wrong type

        # Multi-label
        labels = Labels(["red", "green", "blue"], many=True)
        assert labels.validate([0, 2]) == ["red", "blue"]
        with pytest.raises(ValueError):
            labels.validate(0)  # Wrong type
        with pytest.raises(ValueError):
            labels.validate([3])  # Out of range

    def test_labels_indexed_labels(self):
        """Test getting indexed labels."""
        # Raw values
        labels = Labels(["red", "green", "blue"])
        assert labels.get_indexed_labels() == {
            0: "'red'",
            1: "'green'",
            2: "'blue'",
        }

        # Enum values
        labels = Labels(Colors)
        assert labels.get_indexed_labels() == {
            0: "'red'",
            1: "'green'",
            2: "'blue'",
        }

        # Mixed types
        labels = Labels(["string", 42, True])
        assert labels.get_indexed_labels() == {
            0: "'string'",
            1: "42",
            2: "True",
        }


class TestPythonFunctionAnnotations:
    def test_resolves_string_return_annotations(self):
        python_function = PythonFunction.from_function(build_future_model)
        assert python_function.return_annotation is FutureModel

    def test_works_normally_without_future_annotations(self):
        class PlainModel(BaseModel): ...

        def build_plain_model() -> PlainModel:
            return PlainModel()

        python_function = PythonFunction.from_function(build_plain_model)
        assert python_function.return_annotation is PlainModel

    def test_no_return_annotation_returns_empty(self):
        def no_return_annotation():
            pass

        python_function = PythonFunction.from_function(no_return_annotation)
        assert python_function.return_annotation is inspect.Signature.empty

    def test_unresolvable_forward_ref_falls_back(self):
        """When get_type_hints cannot resolve a forward ref, fall back to sig.return_annotation."""
        # Simulate a function with a string annotation that cannot be resolved
        def unresolvable() -> "NonExistentType":  # noqa: F821
            pass

        python_function = PythonFunction.from_function(unresolvable)
        # Should fall back to the string annotation rather than crashing
        assert python_function.return_annotation == "NonExistentType"
