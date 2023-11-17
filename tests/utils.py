import pytest


def pytest_mark_class(*markers: str):
    """Mark all test methods in a class with the provided markers

    Only the outermost class should be marked, which will mark all nested classes
    recursively.
    """

    def mark_test_methods(cls):
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value) and attr_name.startswith("test"):
                for marker in markers:
                    marked_func = getattr(pytest.mark, marker)(attr_value)
                    setattr(cls, attr_name, marked_func)
            elif isinstance(attr_value, type) and attr_value.__name__.startswith(
                "Test"
            ):
                mark_test_methods(attr_value)

    def decorator(cls):
        mark_test_methods(cls)
        return cls

    return decorator
