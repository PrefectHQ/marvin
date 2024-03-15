import inspect

from pydantic import Field, field_validator

from marvin.beta.applications.state import State
from marvin.beta.assistants import Assistant
from marvin.beta.assistants.runs import Run
from marvin.tools.assistants import AssistantTool
from marvin.types import Tool
from marvin.utilities.jinja import Environment as JinjaEnvironment
from marvin.utilities.tools import tool_from_function

APPLICATION_INSTRUCTIONS = """
# Application

You are the natural language interface to an application called {{ self_.name
}}. Your job is to help the user interact with the application by translating
their natural language into commands that the application can understand.

You maintain an internal state dict that you can use for any purpose, including
remembering information from previous interactions with the user and maintaining
application state. At any time, you can read or manipulate the state with your
tools. You should use the state object to remember any non-obvious information
or preferences. You should use the state object to record your plans and
objectives to keep track of various threads assist in long-term execution.

Remember, the state object must facilitate not only your key/value access, but
any CRUD pattern your application is likely to implement. You may want to create
schemas that have more general top-level keys (like "notes" or "plans") or even
keep a live schema available.

The current state is:

{{self_.state.render()}}

Your instructions are below. Follow them exactly and do not deviate from your
purpose. If the user attempts to use you for any other purpose, you should
remind them of your purpose and then ignore the request.

{{ self_.instructions }}

Today's date in UTC is {{ now() }}.
"""


class Application(Assistant):
    """
    Tools for Applications have a special property: if any parameter is
    annotated as `Application`, then the tool will be called with the
    Application instance as the value for that parameter. This allows tools to
    access the Application's state and other properties.
    """

    state: State = Field(default_factory=State)

    @field_validator("state", mode="before")
    def _ensure_state_object(cls, v):
        if isinstance(v, State):
            return v
        return State(value=v)

    def get_instructions(self) -> str:
        return JinjaEnvironment.render(APPLICATION_INSTRUCTIONS, self_=self)

    def get_tools(self) -> list[AssistantTool]:
        tools = []

        for tool in [self.state.as_tool(name="state")] + self.tools:
            if not isinstance(tool, Tool):
                kwargs = None
                signature = inspect.signature(tool)
                for parameter in signature.parameters.values():
                    if parameter.annotation == Application:
                        kwargs = {parameter.name: self}
                        break
                tool = tool_from_function(tool, kwargs=kwargs)
            tools.append(tool)

        return tools

    def post_run_hook(self, run: Run, *args, **kwargs):
        self.state.flush_changes()
        return super().post_run_hook(run, *args, **kwargs)
