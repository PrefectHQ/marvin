from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Literal

import pytest

from marvin.utilities.types import (
    AutoDataClass,
    Labels,
    create_enum,
    get_classifier_type,
    get_labels,
    is_classifier,
)


class TestClassification:
    def test_create_enum_from_list(self):
        """Test creating an enum from a list."""
        enum_cls = create_enum(["a", "b", "c"])
        assert issubclass(enum_cls, Enum)
        assert [m.name for m in enum_cls] == ["LABEL_0", "LABEL_1", "LABEL_2"]
        assert [m.value for m in enum_cls] == ["a", "b", "c"]

    def test_create_enum_from_tuple(self):
        """Test creating an enum from a tuple."""
        enum_cls = create_enum(("x", "y", "z"))
        assert issubclass(enum_cls, Enum)
        assert [m.name for m in enum_cls] == ["LABEL_0", "LABEL_1", "LABEL_2"]
        assert [m.value for m in enum_cls] == ["x", "y", "z"]

    def test_create_enum_from_set(self):
        """Test creating an enum from a set."""
        enum_cls = create_enum({"p", "q", "r"})
        assert issubclass(enum_cls, Enum)
        values = {m.value for m in enum_cls}
        assert values == {"p", "q", "r"}

    def test_create_enum_with_custom_objects(self):
        """Test creating an enum with custom objects as values."""

        class Point:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        points = [Point(1, 2), Point(3, 4)]
        enum_cls = create_enum(points)
        assert [m.name for m in enum_cls] == ["LABEL_0", "LABEL_1"]
        assert enum_cls["LABEL_0"].value.x == 1
        assert enum_cls["LABEL_1"].value.y == 4

    def test_is_classifier(self):
        """Test classifier type detection."""
        # Test Enum
        enum_cls = create_enum(["a", "b"])
        assert is_classifier(enum_cls)
        assert is_classifier(list[enum_cls])

        # Test Literal
        assert is_classifier(Literal["x", "y"])
        assert is_classifier(list[Literal["x", "y"]])

        # Test non-classifiers
        assert not is_classifier(str)
        assert not is_classifier(list[str])
        assert not is_classifier(int)

    def test_get_labels(self):
        """Test extracting labels from classifier types."""
        # Test Enum
        enum_cls = create_enum(["a", "b", "c"])
        assert get_labels(enum_cls) == ("a", "b", "c")
        assert get_labels(list[enum_cls]) == ("a", "b", "c")

        # Test Literal
        assert get_labels(Literal["x", "y"]) == ("x", "y")
        assert get_labels(list[Literal["x", "y"]]) == ("x", "y")

        # Test non-classifiers
        assert get_labels(str) is None
        assert get_labels(list[str]) is None

    def test_get_classifier_type(self):
        """Test getting validation types for classifiers."""
        # Test single-label
        enum_cls = create_enum(["a", "b"])
        assert get_classifier_type(enum_cls) == int
        assert get_classifier_type(Literal["x", "y"]) == int

        # Test multi-label
        assert get_classifier_type(list[enum_cls]) == list[int]
        assert get_classifier_type(list[Literal["x", "y"]]) == list[int]


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


class TestLabels:
    def test_labels_basic_creation(self):
        """Test creating basic Labels instance."""
        labels = Labels(["a", "b", "c"])
        assert labels.values == ["a", "b", "c"]
        assert not labels.many

    def test_labels_with_many(self):
        """Test creating Labels with many=True."""
        labels = Labels(["a", "b", "c"], many=True)
        assert labels.values == ["a", "b", "c"]
        assert labels.many
