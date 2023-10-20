from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_openai():
    with (
        patch(
            "openai.ChatCompletion.create", MagicMock(spec=["create"])
        ) as mock_create,
        patch(
            "openai.ChatCompletion.acreate", MagicMock(spec=["acreate"])
        ) as mock_acreate,
    ):
        yield mock_create, mock_acreate


class TestRequests:
    pass


class TestResponses:
    pass
