import jsonpatch
import pytest
from marvin.components.ai_application.base import (
    AIApplication,
    AppPlan,
    FreeformState,
    TaskState,
    UpdatePlan,
    UpdateState,
)


class TestJSONPatch:
    def test_update_app_state_valid_patch(self):
        app = AIApplication(
            state=FreeformState(state={"foo": "bar"}), description="test app"
        )
        tool = UpdateState(app=app)
        tool.run([{"op": "replace", "path": "/state/foo", "value": "baz"}])
        assert app.state.dict() == {"state": {"foo": "baz"}}

    def test_update_app_state_invalid_patch(self):
        app = AIApplication(
            state=FreeformState(state={"foo": "bar"}), description="test app"
        )
        tool = UpdateState(app=app)
        with pytest.raises(jsonpatch.InvalidJsonPatch):
            tool.run([{"op": "invalid_op", "path": "/state/foo", "value": "baz"}])
        assert app.state.dict() == {"state": {"foo": "bar"}}

    def test_update_app_state_non_existent_path(self):
        app = AIApplication(
            state=FreeformState(state={"foo": "bar"}), description="test app"
        )
        tool = UpdateState(app=app)
        with pytest.raises(jsonpatch.JsonPatchConflict):
            tool.run([{"op": "replace", "path": "/state/baz", "value": "qux"}])
        assert app.state.dict() == {"state": {"foo": "bar"}}


class TestPlanJSONPatch:
    def test_update_app_plan_valid_patch(self):
        app = AIApplication(
            plan=AppPlan(
                tasks=[{"id": 1, "description": "test task", "state": "IN_PROGRESS"}]
            ),
            description="test app",
        )
        tool = UpdatePlan(app=app)
        tool.run([{"op": "replace", "path": "/tasks/0/state", "value": "COMPLETED"}])
        assert app.plan.dict() == {
            "tasks": [
                {
                    "id": 1,
                    "description": "test task",
                    "state": TaskState.COMPLETED,
                    "upstream_task_ids": None,
                    "parent_task_id": None,
                }
            ],
            "notes": [],
        }

    def test_update_app_plan_invalid_patch(self):
        app = AIApplication(
            plan=AppPlan(
                tasks=[{"id": 1, "description": "test task", "state": "IN_PROGRESS"}]
            ),
            description="test app",
        )
        tool = UpdatePlan(app=app)
        with pytest.raises(jsonpatch.JsonPatchException):
            tool.run(
                [{"op": "invalid_op", "path": "/tasks/0/state", "value": "COMPLETED"}]
            )
        assert app.plan.dict() == {
            "tasks": [
                {
                    "id": 1,
                    "description": "test task",
                    "state": TaskState.IN_PROGRESS,
                    "upstream_task_ids": None,
                    "parent_task_id": None,
                }
            ],
            "notes": [],
        }

    def test_update_app_plan_non_existent_path(self):
        app = AIApplication(
            plan=AppPlan(
                tasks=[{"id": 1, "description": "test task", "state": "IN_PROGRESS"}]
            ),
            description="test app",
        )
        tool = UpdatePlan(app=app)
        with pytest.raises(jsonpatch.JsonPointerException):
            tool.run(
                [{"op": "replace", "path": "/tasks/1/state", "value": "COMPLETED"}]
            )
        assert app.plan.dict() == {
            "tasks": [
                {
                    "id": 1,
                    "description": "test task",
                    "state": TaskState.IN_PROGRESS,
                    "upstream_task_ids": None,
                    "parent_task_id": None,
                }
            ],
            "notes": [],
        }
