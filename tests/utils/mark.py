import pytest


def pytest_mark_class(marker):
    def decorator(cls):
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value) and attr_name.startswith("test"):
                setattr(cls, attr_name, pytest.mark.llm(attr_value))
        return cls

    return decorator
