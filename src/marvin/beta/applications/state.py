import json
import textwrap
from typing import Optional, Union

from jsonpatch import JsonPatch
from pydantic import BaseModel, Field

from marvin.requests import Tool
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
    value: Union[BaseModel, dict] = {}

    def render(self) -> str:
        if self.get_schema():
            return self.value.model_dump_json()
        return repr(self.value)

    def get_schema(self) -> Optional[dict]:
        if isinstance(self.value, BaseModel):
            return self.value.model_json_schema()

    def set_state(self, state: Union[BaseModel, dict]):
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

    def as_tool(self) -> "Tool":
        schema = self.get_schema()
        if schema:
            description = textwrap.dedent(
                "Update the application state using JSON Patch documents. Updates will"
                " fail if they do not comply with the state schema. The state schema"
                " is:\n\n```json\n{schema}\n```"
            ).format(schema=json.dumps(schema, indent=2))

        else:
            description = "Update the application state using JSON Patch documents."
        return tool_from_function(
            self.update_state_jsonpatches, description=description
        )
