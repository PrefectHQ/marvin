import inspect
import json
from typing import Optional, Union

from jsonpatch import JsonPatch
from pydantic import BaseModel, Field, PrivateAttr, SerializeAsAny

import marvin.settings
from marvin.types import FunctionTool
from marvin.utilities.tools import tool_from_function


class JSONPatchModel(BaseModel, populate_by_name=True):
    """A JSON Patch document.

    Attributes:
        op: The operation to perform.
        path: The path to the value to update.
        value: The value to update the path to.
        from_: The path to the value to copy from.
    """

    op: str
    path: str
    value: Union[str, float, int, bool, list, dict, None] = None
    from_: Optional[str] = Field(None, alias="from")


class State(BaseModel):
    value: SerializeAsAny[Union[BaseModel, dict]] = {}
    _last_saved_value: Optional[Union[BaseModel, dict]] = PrivateAttr(None)

    def render(self) -> str:
        if self.get_schema():
            return self.value.model_dump_json(indent=2)
        return repr(self.value)

    def get_schema(self) -> Optional[dict]:
        if isinstance(self.value, BaseModel):
            return self.value.model_json_schema()

    def flush_changes(self):
        """
        Detects if any changes have been made to the state without saving it (calling "set_state") and saves them.
        """
        if self._last_saved_value != self.value:
            self.set_state(self.value)

    def set_state(self, state: Union[BaseModel, dict]):
        self._last_saved_value = self.value
        self.value = state

    def update_state_jsonpatches(self, patches: list[JSONPatchModel]):
        """
        Update the application state using JSON Patch documents.

        Args:
            app: The application to update.
            patches: A list of JSON Patch documents.
        """
        patch = JsonPatch(patches)
        if self.get_schema():
            state = patch.apply(self.value.model_dump())
            state = type(self.value)(**state)
        else:
            state = patch.apply(self.value)
        self.set_state(state)
        return "Application state updated successfully!"

    def as_tool(self, name: str = None) -> "FunctionTool":
        if name is None:
            name = "state"
        schema = self.get_schema()
        if schema:
            description = inspect.cleandoc(
                f"Update the {name} object using JSON Patch documents. Updates will"
                " fail if they do not comply with the following"
                " schema:\n\n```json\n{schema}\n```"
            ).format(schema=json.dumps(schema, indent=2))[
                : marvin.settings.max_tool_description_length
            ]

        else:
            description = "Update the application state using JSON Patch documents."
        return tool_from_function(
            self.update_state_jsonpatches,
            name=f"update_{name}",
            description=description,
        )
