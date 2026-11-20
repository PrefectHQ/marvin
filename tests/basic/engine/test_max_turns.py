from unittest.mock import AsyncMock

import pytest

from marvin import Agent, Task
from marvin.engine.orchestrator import Orchestrator


async def test_task_can_complete_on_last_allowed_turn(test_model):
    task = Task("Answer the prompt", agents=[Agent(model=test_model)])
    test_model.custom_output_args = {"task_id": task.id, "result": "done"}

    results = await Orchestrator(tasks=[task]).run(max_turns=1)

    assert len(results) == 1
    assert task.is_successful()
    assert task.result == "done"


async def test_turn_limit_still_errors_with_incomplete_task(test_model, monkeypatch):
    task = Task("Answer the prompt", agents=[Agent(model=test_model)])
    run_once = AsyncMock()
    orchestrator = Orchestrator(tasks=[task])
    monkeypatch.setattr(orchestrator, "run_once", run_once)

    with pytest.raises(ValueError, match="Max agent turns reached"):
        await orchestrator.run(max_turns=1)

    run_once.assert_awaited_once()
    assert task.is_incomplete()
