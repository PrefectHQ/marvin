import pytest
import inspect
from marvin.functions import Function


class TestFunctions:
    def test_signature(self):
        def fn(x, y=10):
            return x + y

        f = Function(fn=fn)
        assert f.signature == inspect.signature(fn)
