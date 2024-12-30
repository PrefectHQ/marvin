from dataclasses import asdict, is_dataclass

import pytest

from marvin.utilities.types import AutoDataClass


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
