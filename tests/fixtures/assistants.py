from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_default_run_handler_class():
    """Return an empty default handler instead of a print handler to avoid
    printing assistant output during tests"""
    mock = Mock()
    mock.return_value = None
    with patch("marvin.beta.assistants.assistants.default_run_handler_class", new=mock):
        yield
