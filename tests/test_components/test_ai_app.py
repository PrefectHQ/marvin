import jsonpatch
import pytest
from marvin.components.ai_application import (
    AIApplication,
    AppPlan,
    FreeformState,
    JSONPatchModel,
    TaskState,
    UpdatePlan,
    UpdateState,
)
from marvin.tools import Tool

from tests.utils.mark import pytest_mark_class


class TestStateJSONPatch:
    def test_update_app_state_valid_patch(self):
        app = AIApplication(
            state=FreeformState(state={"foo": "bar"}), description="test app"
        )
        tool = UpdateState(app=app)
        tool.run(
            [JSONPatchModel(**{"op": "replace", "path": "/state/foo", "value": "baz"})]
        )
        assert app.state.dict() == {"state": {"foo": "baz"}}

    def test_update_app_state_invalid_patch(self):
        app = AIApplication(
            state=FreeformState(state={"foo": "bar"}), description="test app"
        )
        tool = UpdateState(app=app)
        with pytest.raises(jsonpatch.InvalidJsonPatch):
            tool.run(
                [
                    JSONPatchModel(
                        **{"op": "invalid_op", "path": "/state/foo", "value": "baz"}
                    )
                ]
            )
        assert app.state.dict() == {"state": {"foo": "bar"}}

    def test_update_app_state_non_existent_path(self):
        app = AIApplication(
            state=FreeformState(state={"foo": "bar"}), description="test app"
        )
        tool = UpdateState(app=app)
        with pytest.raises(jsonpatch.JsonPatchConflict):
            tool.run(
                [
                    JSONPatchModel(
                        **{"op": "replace", "path": "/state/baz", "value": "qux"}
                    )
                ]
            )
        assert app.state.dict() == {"state": {"foo": "bar"}}


@pytest_mark_class("llm")
class TestUpdateState:
    def test_keep_app_state(self):
        app = AIApplication(
            name="location tracker app",
            state=FreeformState(state={"San Francisco": False}),
            description="keep track of where I've been",
        )

        app("I went to San Francisco")

        assert app.state.dict() == {"state": {"San Francisco": "True"}}

        app("oh also I went to San Jose")

        assert app.state.dict() == {
            "state": {"San Francisco": "True", "San Jose": "True"}
        }

    def test_keep_app_state_undo_previous_patch(self):
        app = AIApplication(
            name="location tracker app",
            state=FreeformState(state={"San Francisco": "False"}),
            description="keep track of where I've been",
        )

        app("I went to San Francisco")

        assert app.state.dict() == {"state": {"San Francisco": "True"}}

        app("oh actually I lied about going to SF, but I did go to San Jose")

        assert app.state.dict() == {
            "state": {"San Francisco": "False", "San Jose": "True"}
        }


class TestPlanJSONPatch:
    def test_update_app_plan_valid_patch(self):
        app = AIApplication(
            plan=AppPlan(
                tasks=[{"id": 1, "description": "test task", "state": "IN_PROGRESS"}]
            ),
            description="test app",
        )
        tool = UpdatePlan(app=app)
        tool.run(
            [
                JSONPatchModel(
                    **{"op": "replace", "path": "/tasks/0/state", "value": "COMPLETED"}
                )
            ]
        )
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
                [
                    JSONPatchModel(
                        **{
                            "op": "invalid_op",
                            "path": "/tasks/0/state",
                            "value": "COMPLETED",
                        }
                    )
                ]
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
                [
                    JSONPatchModel(
                        **{
                            "op": "replace",
                            "path": "/tasks/1/state",
                            "value": "COMPLETED",
                        }
                    )
                ]
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


@pytest_mark_class("llm")
class TestUpdatePlan:
    def test_keep_app_plan(self):
        app = AIApplication(
            name="Zoo planner app",
            plan=AppPlan(
                tasks=[
                    {
                        "id": 1,
                        "description": "Visit tigers",
                        "state": TaskState.IN_PROGRESS,
                    },
                    {
                        "id": 2,
                        "description": "Visit giraffes",
                        "state": TaskState.PENDING,
                    },
                ]
            ),
            description="plan my visit to the zoo",
        )

        app(
            "Actually I heard the tigers ate Carol Baskin's husband - I think I'll skip"
            " that."
        )

        assert [task["state"] for task in app.plan.dict()["tasks"]] == [
            TaskState.SKIPPED,
            TaskState.PENDING,
        ]

        app("Dude i just saw the giraffes and their necks are so long!")

        assert [task["state"] for task in app.plan.dict()["tasks"]] == [
            TaskState.SKIPPED,
            TaskState.COMPLETED,
        ]


@pytest_mark_class("llm")
class TestUseCallable:
    def test_use_sync_fn(self):
        def get_schleeb():
            return 42

        app = AIApplication(
            name="Schleeb app",
            tools=[get_schleeb],
            state_enabled=False,
            plan_enabled=False,
            description="answer user questions",
        )

        assert "42" in app("what is the value of schleeb?").content

    def test_use_async_fn(self):
        async def get_schleeb():
            return 42

        app = AIApplication(
            name="Schleeb app",
            tools=[get_schleeb],
            state_enabled=False,
            plan_enabled=False,
            description="answer user questions",
        )

        assert "42" in app("what is the value of schleeb?").content


@pytest_mark_class("llm")
class TestUseTool:
    class GetSchleeb(Tool):
        async def run(self):
            return 42

    def test_use_tool(self):
        app = AIApplication(
            name="Schleeb app",
            tools=[self.GetSchleeb()],
            state_enabled=False,
            plan_enabled=False,
            description="answer user questions",
        )

        assert "42" in app("what is the value of schleeb?").content
