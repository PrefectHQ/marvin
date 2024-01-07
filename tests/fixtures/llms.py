import pytest
from marvin.settings import temporary_settings


@pytest.fixture
def gpt_4():
    """
    Uses GPT 4 for the duration of the test
    """
    with temporary_settings(openai__chat__completions__model="gpt-4-1106-preview"):
        yield
