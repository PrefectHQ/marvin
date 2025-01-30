import marvin


def test_summarize_text():
    result = marvin.summarize("I bought a new car")
    assert isinstance(result, str)


def test_summarize_bullets():
    result = marvin.summarize(
        "I bought a new car", instructions='return two "-" bullet points'
    )
    assert result.startswith("-")
    assert "\n-" in result
