import pytest
from pydantic_ai import models

import marvin


async def test_run_tasks_stream_raises_when_empty():
    with pytest.raises(
        ValueError, match="Cannot run orchestrator without tasks/actors"
    ):
        await marvin.run_tasks_async([])

    events = []
    with pytest.raises(
        ValueError, match="Cannot run orchestrator without tasks/actors"
    ):
        async for event in marvin.run_tasks_stream([]):
            events.append(event.type)

    assert events == ["orchestrator-start"]


async def test_run_tasks_stream_raises_original_model_error(test_model, monkeypatch):
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    failure = RuntimeError("test model failed")

    def fail_stream(*args, **kwargs):
        raise failure

    monkeypatch.setattr(test_model, "request_stream", fail_stream)
    task = marvin.Task("Answer the prompt", agents=[marvin.Agent(model=test_model)])
    events = []

    with pytest.raises(RuntimeError) as exc_info:
        async for event in marvin.run_tasks_stream([task]):
            events.append(event.type)

    assert exc_info.value is failure
    assert events[-2:] == ["orchestrator-error", "orchestrator-end"]
