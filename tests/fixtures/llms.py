import marvin
import marvin.config
import pytest


@pytest.fixture
def gpt_4():
    """
    Uses GPT 4 for the duration of the test
    """
    with marvin.config.temporary_settings(
        llm_model="gpt-4",
        llm_backend=marvin.config.LLMBackend.OpenAIChat,
    ):
        yield
