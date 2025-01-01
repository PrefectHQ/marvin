import enum
from dataclasses import asdict, is_dataclass
from typing import Literal

import pytest

from marvin.utilities.types import (
    AutoDataClass,
    Labels,
    as_classifier,
    is_classifier,
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


class TestAutoDataClass:
    def test_basic_autodataclass(self):
        """Test basic AutoDataClass functionality."""

        class SimpleClass(AutoDataClass):
            field1: str
            field2: int = 42

        obj = SimpleClass(field1="test")
        assert is_dataclass(obj)
        assert obj.field1 == "test"
        assert obj.field2 == 42
        assert asdict(obj) == {"field1": "test", "field2": 42}

    def test_autodataclass_config(self):
        """Test AutoDataClass configuration options."""

        class ConfiguredClass(AutoDataClass):
            _dataclass_config = {"frozen": True}
            field: str

        obj = ConfiguredClass(field="test")
        assert is_dataclass(obj)

        # Test frozen=True by attempting to modify
        with pytest.raises(Exception):
            obj.field = "new value"

    def test_autodataclass_kw_only(self):
        """Test AutoDataClass with kw_only configuration."""

        class KwOnlyClass(AutoDataClass):
            _dataclass_config = {"kw_only": True}
            field1: str
            field2: int

        # Should work with keyword arguments
        obj = KwOnlyClass(field1="test", field2=42)
        assert obj.field1 == "test"
        assert obj.field2 == 42

        # Should fail with positional arguments
        with pytest.raises(TypeError):
            KwOnlyClass("test", 42)

    def test_autodataclass_nested(self):
        """Test nested AutoDataClass instances."""

        class Inner(AutoDataClass):
            value: int

        class Outer(AutoDataClass):
            inner: Inner
            name: str

        inner = Inner(value=42)
        outer = Outer(inner=inner, name="test")

        assert is_dataclass(outer)
        assert is_dataclass(outer.inner)
        assert outer.inner.value == 42
        assert outer.name == "test"
        assert asdict(outer) == {"inner": {"value": 42}, "name": "test"}

    def test_autodataclass_config_inheritance(self):
        """Test that _dataclass_config is properly inherited and merged."""

        class Parent(AutoDataClass):
            _dataclass_config = {"frozen": True}
            x: int

        class Child(Parent):
            _dataclass_config = {"kw_only": True}
            y: str

        # Child should inherit parent's frozen=True and combine with its own kw_only=True
        assert Child._dataclass_config == {"frozen": True, "kw_only": True}

        # Test that config is applied correctly
        obj = Child(x=1, y="test")
        assert obj.x == 1
        assert obj.y == "test"

        # Should fail with positional args (kw_only=True)
        with pytest.raises(TypeError):
            Child(1, "test")

        # Should fail when trying to modify (frozen=True)
        with pytest.raises(Exception):
            obj.x = 2
