import pydantic_ai.models
import pytest
from pydantic_ai.models.test import TestModel


@pytest.fixture(autouse=True)
def prevent_model_requests():
    with pydantic_ai.models.override_allow_model_requests(False):
        yield


@pytest.fixture(autouse=True)
def autouse_test_model(test_model: TestModel):
    yield test_model
