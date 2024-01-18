import pytest
from marvin.utilities.retries import retry_with_fallback
from pydantic import BaseModel


class SomeFancyType(BaseModel):
    some_field: str


class LLMMadLib(BaseModel):
    what_i_want: SomeFancyType


@pytest.fixture
def retry_configs():
    return [
        ({"model_kwargs": {"model": "gpt-3.5-turbo", "temperature": 0.7}}, 3),
        ({"model_kwargs": {"model": "gpt-3.5-turbo", "temperature": 0.3}}, 3),
        ({"model_kwargs": {"model": "gpt-4", "temperature": 0.0}}, 2),
    ]


def test_continuous_failure_and_error_propagation(retry_configs, capsys):
    @retry_with_fallback(retry_configs, lambda e: isinstance(e, RuntimeError))
    def always_failing_function(model_kwargs=None):
        raise RuntimeError("Consistent failure")

    with pytest.raises(RuntimeError) as exc_info:
        always_failing_function()

    assert "Consistent failure" in str(exc_info.value)
    assert "All retries have failed" in str(exc_info.value)
    assert capsys.readouterr().out.count("Retrying") == sum(
        retries for _, retries in retry_configs
    )


def test_success_without_retries(retry_configs, capsys):
    @retry_with_fallback(retry_configs, lambda e: isinstance(e, RuntimeError))
    def immediate_success_function(model_kwargs=None):
        return "Immediate success"

    assert immediate_success_function() == "Immediate success"
    assert "Retrying" not in capsys.readouterr().out


def test_success_after_specific_retries(retry_configs, capsys):
    failure_count = [0]

    @retry_with_fallback(retry_configs, lambda e: isinstance(e, RuntimeError))
    def success_after_retries_function(model_kwargs=None):
        if failure_count[0] < 4:  # Fail for the first 4 attempts
            failure_count[0] += 1
            raise RuntimeError("Temporary failure")
        return "Success after retries"

    assert success_after_retries_function() == "Success after retries"
    captured = capsys.readouterr()
    assert captured.out.count("Retrying") == 4  # 4 retries before success


def test_user_provided_arguments_prioritized(retry_configs, capsys):
    @retry_with_fallback(retry_configs, lambda e: isinstance(e, RuntimeError))
    def something_with_prioritized_args(model_kwargs=None):
        assert model_kwargs["temperature"] == 0.9  # User-provided argument
        raise RuntimeError("Triggering retry")

    with pytest.raises(RuntimeError):
        something_with_prioritized_args(
            model_kwargs={"model": "gpt-3.5-turbo", "temperature": 0.9}
        )

    captured = capsys.readouterr()
    # Ensure that the retry logic is still applied
    assert captured.out.count("Retrying") == sum(
        retries for _, retries in retry_configs
    )
