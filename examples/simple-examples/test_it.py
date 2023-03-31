from marvin import ai_fn


@ai_fn()
def test_it() -> list[str]:
    """
    Returns a pytest unit tests this function:

    def adder(num1 -> int, num2 -> int) -> int:
        returns num1 + num2

    """


print(test_it())

# ['def test_adder():', '    assert adder(2, 3) == 5', '    assert adder(-1, 1) == 0', '    assert adder(-3, -3) == -6']
