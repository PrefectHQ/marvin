import jsonpatch
import pytest
from marvin.primitives.ai_application.base import (
    AIApplication,
    FreeformState,
    UpdateAppState,
)


class TestJSONPatch:
    def test_update_app_state_valid_patch(self):
        app = AIApplication(
            state=FreeformState(state={"foo": "bar"}), description="test app"
        )
        tool = UpdateAppState(app=app)
        tool.run([{"op": "replace", "path": "/state/foo", "value": "baz"}])
        assert app.state.dict() == {"state": {"foo": "baz"}}

    def test_update_app_state_invalid_patch(self):
        app = AIApplication(
            state=FreeformState(state={"foo": "bar"}), description="test app"
        )
        tool = UpdateAppState(app=app)
        with pytest.raises(jsonpatch.InvalidJsonPatch):
            tool.run([{"op": "invalid_op", "path": "/state/foo", "value": "baz"}])
        assert app.state.dict() == {"state": {"foo": "bar"}}

    def test_update_app_state_non_existent_path(self):
        app = AIApplication(
            state=FreeformState(state={"foo": "bar"}), description="test app"
        )
        tool = UpdateAppState(app=app)
        with pytest.raises(jsonpatch.JsonPatchConflict):
            tool.run([{"op": "replace", "path": "/state/baz", "value": "qux"}])
        assert app.state.dict() == {"state": {"foo": "bar"}}
