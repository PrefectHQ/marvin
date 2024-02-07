from marvin.beta.applications import Application
from marvin.beta.applications.state import State
from marvin.utilities.logging import get_logger
from pydantic import BaseModel

state_logger = get_logger("app.state_transitions")


audit_log = []


class AppState(State):
    def set_state(self, state: BaseModel | dict):
        if self.value != self._last_saved_value:
            state_logger.info(
                f"state changed from {self._last_saved_value} to {self.value}"
            )
            audit_log.append(self)
        return super().set_state(state)


if __name__ == "__main__":
    with Application(
        name="Marvin", state=AppState(value={"favorite_number": 0})
    ) as app:
        app.say("please set state to favorite_number to 42")
        assert app.state.value == audit_log[0].value == {"favorite_number": 42}
