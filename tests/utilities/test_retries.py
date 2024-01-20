import pytest
from marvin.utilities.retries import retry_with_fallback
from pydantic import BaseModel


class SomeFancyType(BaseModel):
    some_field: str


RETRY_CONFIGS = [
    {"model_kwargs": {"model": "gpt-3.5-turbo", "temperature": 0.7}, "retries": 3},
    {"model_kwargs": {"model": "gpt-3.5-turbo", "temperature": 0.3}, "retries": 3},
    {"model_kwargs": {"model": "gpt-4", "temperature": 0.0}, "retries": 2},
]


@pytest.fixture
def retry_configs():
    return RETRY_CONFIGS


def test_continuous_failure_and_error_propagation(retry_configs):
    @retry_with_fallback(retry_configs, error_handler=lambda _: True)
    def always_failing_function(model_kwargs):
        raise RuntimeError("Consistent failure")

    with pytest.raises(RuntimeError) as exc_info:
        always_failing_function(
            model_kwargs={"model": "gpt-3.5-turbo", "temperature": 0.9}
        )

    assert "Consistent failure" in str(exc_info.value)
    assert "All retries have failed" in str(exc_info.value)


def test_success_without_retries(retry_configs):
    @retry_with_fallback(retry_configs)
    def immediate_success_function(model_kwargs):
        return "Immediate success"

    assert (
        immediate_success_function(
            model_kwargs={"model": "gpt-3.5-turbo", "temperature": 0.9}
        )
        == "Immediate success"
    )


def test_success_after_specific_retries(retry_configs):
    failure_count = [0]

    @retry_with_fallback(retry_configs, error_handler=lambda _: True)
    def success_after_retries_function(model_kwargs):
        if failure_count[0] < 4:  # Fail for the first 4 attempts
            failure_count[0] += 1
            raise RuntimeError("Temporary failure")
        return "Success after retries"

    assert (
        success_after_retries_function(
            model_kwargs={"model": "gpt-3.5-turbo", "temperature": 0.9}
        )
        == "Success after retries"
    )


def test_user_provided_arguments_prioritized(retry_configs):
    count = 0
    first_model = "gpt-3.5-turbo"
    first_temperature = 0.9

    @retry_with_fallback(retry_configs)
    def something_with_prioritized_args(model_kwargs):
        nonlocal count
        count += 1
        return (model_kwargs["model"], model_kwargs["temperature"])

    assert (first_model, first_temperature) == something_with_prioritized_args(
        model_kwargs={"model": first_model, "temperature": first_temperature}
    )
    assert count == 1
