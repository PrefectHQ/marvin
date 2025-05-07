from functools import partial  # For checking the tool function

from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.tools import (
    Tool as PydanticAiTool,  # Alias to avoid conflict if Tool is defined locally
)

from marvin._internal.integrations.mcp import _mcp_tool_wrapper  # To check the function
from marvin.agents import Agent
from marvin.engine.events import ToolCallEvent
from marvin.handlers.handlers import AsyncHandler

# Requires Deno: `deno install -A ... jsr:@pydantic/mcp-run-python`
# This server provides a `run_python_code` tool.
run_python_server = MCPServerStdio(
    command="deno",
    args=["run", "-A", "jsr:@pydantic/mcp-run-python", "stdio"],
)


async def test_mcp_tool_usage_and_clean_output():
    """
    Tests that an Agent using an MCP tool (run_python_code via Deno server)
    1. Emits a single, correctly populated ToolCallEvent.
    2. The event's tool is a PydanticAiTool whose function is the MCP wrapper setup.
    3. Correctly processes the tool's output to provide a clean final result.
    """

    tool_call_events_captured: list[ToolCallEvent] = []

    class MCPToolCallCaptureHandler(AsyncHandler):
        async def on_tool_call(self, event: ToolCallEvent):
            if event.message.tool_name == "run_python_code":
                tool_call_events_captured.append(event)

    linus = Agent(
        name="TestMCPAgent",
        instructions="Use the available tools to accomplish the user's goal.",
        mcp_servers=[run_python_server],
    )

    task = "Use python to calculate 1 + 1 and return only the numerical result."

    result = await linus.run_async(task, handlers=[MCPToolCallCaptureHandler()])

    assert result == "2", f"Agent final result was not '2'. Got: {result!r}"

    assert len(tool_call_events_captured) == 1, (
        f"Expected 1 'run_python_code' tool call event, got {len(tool_call_events_captured)}. "
        f"Captured events (tool_type, tool_id): {[(type(e.tool).__name__, e.message.tool_call_id) for e in tool_call_events_captured]}"
    )

    the_tool_call_event = tool_call_events_captured[0]

    assert the_tool_call_event.message.tool_name == "run_python_code"
    assert isinstance(the_tool_call_event.tool, PydanticAiTool), (
        f"Tool type was {type(the_tool_call_event.tool).__name__}, expected PydanticAiTool."
    )

    assert hasattr(the_tool_call_event.tool, "function"), (
        "PydanticAiTool instance has no 'function' attribute."
    )
    tool_function_assigned = the_tool_call_event.tool.function

    assert tool_function_assigned.__name__ == "async_wrapped_func_fixed", (
        f"Tool function name was {tool_function_assigned.__name__}, expected 'async_wrapped_func_fixed'."
    )

    assert (
        tool_function_assigned.__defaults__ is not None
        and len(tool_function_assigned.__defaults__) > 0
    ), "async_wrapped_func_fixed should have default arguments."

    bound_partial_from_defaults = tool_function_assigned.__defaults__[0]
    assert isinstance(bound_partial_from_defaults, partial), (
        f"Captured _bound_partial was type {type(bound_partial_from_defaults).__name__}, expected functools.partial."
    )

    assert bound_partial_from_defaults.func is _mcp_tool_wrapper, (
        "The bound partial in the MCP tool wrapper function was not a partial of _mcp_tool_wrapper."
    )

    # Verify arguments if necessary (optional, as the task is simple)
    # assert first_python_call.args_dict() == {'python_code': '1 + 1'} # LLM might generate slightly different code
