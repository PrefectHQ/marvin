import pytest
from marvin.utilities.testing import assert_equal


class TestAssertEqual:
    def test_simple_assert(self):
        assert_equal("hello", "hello")

    def test_simple_assert_fail(self):
        with pytest.raises(AssertionError):
            assert_equal("hello", "goodbye")

    def test_ordered_ints(self):
        assert_equal([1, 2, 3], "a list of three integers")

    def test_ordered_ints_fail(self):
        with pytest.raises(AssertionError):
            assert_equal([2, 1, 3], "a list of three integers in ascending order")

    def test_general_knowledge(self):
        assert_equal(
            "The capital of France is Paris",
            "a sentence about general knowledge",
        )

    def test_geography(self):
        assert_equal(
            ["New York, NY", "Los Angeles, CA", "Chicago, IL"],
            "A list of American cities",
        )
