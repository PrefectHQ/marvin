import pytest

import marvin
from marvin.utilities.asyncio import run_sync


@pytest.mark.parametrize("message", ["provider event loop failed", "provider failed"])
def test_fn_propagates_original_runtime_error(message):
    error = RuntimeError(message)

    @marvin.fn
    def failing_context() -> str:
        raise error

    with pytest.raises(RuntimeError) as exc:
        failing_context()
    assert exc.value is error


@pytest.mark.parametrize("message", ["provider event loop failed", "provider failed"])
def test_run_sync_propagates_original_runtime_error(message):
    error = RuntimeError(message)

    async def failing():
        raise error

    with pytest.raises(RuntimeError) as exc:
        run_sync(failing())
    assert exc.value is error
