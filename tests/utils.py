import pytest


def pytest_mark_class(*markers: str):
    """Mark all test methods in a class with the given markers."""

    def decorator(cls):
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value) and attr_name.startswith("test"):
                for marker in markers:
                    setattr(cls, attr_name, getattr(pytest.mark, marker)(attr_value))
        return cls

    return decorator
