import pytest
from prefect.testing.utilities import prefect_test_harness


@pytest.fixture(scope="session")
def prefect_db():
    with prefect_test_harness():
        yield
