from pydantic_ai.mcp import MCPServerStdio

from marvin.agents import Agent
from marvin.engine.events import ToolCallEvent
from marvin.handlers.handlers import AsyncHandler

git_mcp_server = MCPServerStdio(
    command="uvx",
    args=["mcp-server-git"],
)

EXPECTED_GIT_TOOL_NAME = "git_log"


async def test_mcp_git_server_tool_usage_and_output():
    """
    Tests an Agent using an MCP tool from mcp-server-git (via uvx).
    1. Emits a single, correctly populated ToolCallEvent.
    2. The MCP tool is successfully called and returns valid results.
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

    task = f"Use the {EXPECTED_GIT_TOOL_NAME} tool to get info on the latest commit in the current directory."

    result_string = await linus.run_async(task, handlers=[MCPToolCallCaptureHandler()])

    assert isinstance(result_string, str), (
        f"Expected result to be a string, got {type(result_string)}"
    )
    assert len(result_string) > 0, "Expected non-empty string result from agent."

    assert len(tool_call_events_captured) == 1, (
        f"Expected 1 '{EXPECTED_GIT_TOOL_NAME}' tool call event, got {len(tool_call_events_captured)}. "
        f"Captured events: {[(e.message.tool_name, type(e.tool).__name__, e.message.tool_call_id) for e in tool_call_events_captured]}"
    )

    the_tool_call_event = tool_call_events_captured[0]

    assert the_tool_call_event.message.tool_name == EXPECTED_GIT_TOOL_NAME

    # Verify the tool call has the correct structure regardless of tool implementation
    assert the_tool_call_event.message.tool_call_id is not None
    assert the_tool_call_event.message.args is not None
