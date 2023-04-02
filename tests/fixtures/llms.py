import marvin
import marvin.config
import pytest


@pytest.fixture
def gpt_4():
    """
    Uses GPT 4 for the duration of the test
    """
    with marvin.config.temporary_settings(openai_model_name="gpt-4"):
        yield
