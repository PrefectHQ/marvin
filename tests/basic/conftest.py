import pydantic_ai.models.test
import pytest

from marvin.defaults import override_defaults


@pytest.fixture(autouse=True)
def prevent_model_requests():
    with pydantic_ai.models.override_allow_model_requests(False):
        yield


@pytest.fixture(autouse=True)
def test_model():
    model = pydantic_ai.models.test.TestModel()
    with override_defaults(model=model):
        yield model
