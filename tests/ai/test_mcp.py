from functools import partial

from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.tools import Tool as PydanticAiTool

from marvin._internal.integrations.mcp import _mcp_tool_wrapper
from marvin.agents import Agent
from marvin.engine.events import ToolCallEvent
from marvin.handlers.handlers import AsyncHandler

# Using uvx with mcp-server-git, assuming it's available in CI via uvx
# This server likely provides tools like 'git_log' or 'get_latest_commit_hash'
git_mcp_server = MCPServerStdio(
    command="uvx",
    args=["mcp-server-git"],  # Ensure mcp-server-git is discoverable by uvx
)

# Placeholder for the actual tool name mcp-server-git will provide
# We might need to discover this or make an assumption.
# Common tools from git servers are often 'git_log' or 'get_commit'.
EXPECTED_GIT_TOOL_NAME = "git_log"  # Assuming based on examples


async def test_mcp_git_server_tool_usage_and_output():
    """
    Tests an Agent using an MCP tool from mcp-server-git (via uvx).
    1. Emits a single, correctly populated ToolCallEvent.
    2. The event's tool is a PydanticAiTool whose function is the MCP wrapper setup.
    3. Agent produces a non-empty string result (actual commit details vary).
    """

    tool_call_events_captured: list[ToolCallEvent] = []

    class MCPToolCallCaptureHandler(AsyncHandler):
        async def on_tool_call(self, event: ToolCallEvent):
            if event.message.tool_name == EXPECTED_GIT_TOOL_NAME:
                tool_call_events_captured.append(event)

    linus = Agent(
        name="TestGitMCPAgent",
        instructions="Use available tools to get version control information.",
        mcp_servers=[git_mcp_server],
    )

    # Task that should use a git tool from mcp-server-git
    task = f"Use the {EXPECTED_GIT_TOOL_NAME} tool to get info on the latest commit in the current directory."

    # Default result_type is str
    result_string = await linus.run_async(task, handlers=[MCPToolCallCaptureHandler()])

    assert isinstance(result_string, str), (
        f"Expected result to be a string, got {type(result_string)}"
    )
    assert len(result_string) > 0, "Expected non-empty string result from agent."
    # More specific assertion on result_string content (e.g., contains 'Commit:') might be too brittle.

    assert len(tool_call_events_captured) == 1, (
        f"Expected 1 '{EXPECTED_GIT_TOOL_NAME}' tool call event, got {len(tool_call_events_captured)}. "
        f"Captured events: {[(e.message.tool_name, type(e.tool).__name__, e.message.tool_call_id) for e in tool_call_events_captured]}"
    )

    the_tool_call_event = tool_call_events_captured[0]

    assert the_tool_call_event.message.tool_name == EXPECTED_GIT_TOOL_NAME
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
