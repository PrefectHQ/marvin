import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

import marvin
from marvin.engine.end_turn import PlanSubtasks
from marvin.fns.plan import PlanTask, create_tasks


@pytest.mark.parametrize("parent_id", [0, 5])
async def test_plan_preserves_parent_and_readiness(parent_id: int) -> None:
    outer = marvin.Task("outer")
    branch, leaf = create_tasks(
        [
            PlanTask(id=1, instructions="leaf", parent_id=parent_id),
            PlanTask(id=parent_id, instructions="branch"),
        ],
        agent_map={},
        tool_map={},
        parent_task=outer,
    )

    assert branch.parent is outer
    assert leaf.parent is branch
    assert outer.subtasks == {branch}
    assert leaf.is_ready()
    assert not branch.is_ready()

    await leaf.mark_successful("done")
    assert branch.is_ready()
    assert not outer.is_ready()


async def test_dynamic_plan_preserves_zero_parent(
    test_model: TestModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    test_model.custom_output_args = {
        "result": [
            {"id": 1, "instructions": "leaf", "parent_id": 0},
            {"id": 0, "instructions": "branch"},
        ]
    }
    actor = marvin.Agent(model=test_model)
    outer = marvin.Task("outer", agents=[actor], plan=True)
    (plan_subtasks,) = (
        tool for tool in outer.get_end_turn_tools() if issubclass(tool, PlanSubtasks)
    )

    await plan_subtasks(instructions="Create a branch and leaf").run(
        thread=marvin.Thread(), actor=actor
    )

    (branch,) = outer.subtasks
    (leaf,) = branch.subtasks
    assert branch.instructions == "branch"
    assert leaf.instructions == "leaf"
    assert leaf.is_ready()
    assert not branch.is_ready()

    await leaf.mark_successful("done")
    assert branch.is_ready()
