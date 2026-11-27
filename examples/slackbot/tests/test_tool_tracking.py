import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from prefect.testing.utilities import prefect_test_harness
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.toolsets import AbstractToolset
from slackbot._internal.tool_tracking import TOOL_LIMIT_MESSAGE, ToolCallWatcher


@pytest.fixture(autouse=True, scope="module")
def local_prefect():
    with prefect_test_harness():
        yield


def calls_then_answers(tool_name: str, n: int) -> FunctionModel:
    """A model that calls one tool `n` times in sequence, then answers."""

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if len(messages) <= 2 * n - 1:
            return ModelResponse(parts=[ToolCallPart(tool_name, {})])
        return ModelResponse(parts=[TextPart("done")])

    return FunctionModel(respond)


def tool_results(result) -> list[tuple[str, str]]:
    return [
        (part.outcome, str(part.content))
        for message in result.all_messages()
        for part in message.parts
        if part.part_kind == "tool-return"
    ]


async def test_concurrent_runs_keep_separate_tallies_and_limits():
    both_running = asyncio.Barrier(2)
    executed: list[str] = []

    async def search() -> str:
        executed.append("search")
        await both_running.wait()
        return "found"

    async def lookup() -> str:
        executed.append("lookup")
        await both_running.wait()
        return "found"

    generous = ToolCallWatcher(max_tool_calls=5)
    strict = ToolCallWatcher(max_tool_calls=1)
    original_call_tool = AbstractToolset.call_tool

    first, second = await asyncio.wait_for(
        asyncio.gather(
            Agent(calls_then_answers("search", 1), tools=[search]).run(
                "hi", capabilities=[generous.capability()]
            ),
            Agent(calls_then_answers("lookup", 2), tools=[lookup]).run(
                "hi", capabilities=[strict.capability()]
            ),
        ),
        10,
    )

    assert generous.counts == {"search": 1}
    assert strict.counts == {"lookup": 1}
    assert tool_results(first) == [("success", "found")]
    # the second call is refused as a failed result, not run and not retried
    assert tool_results(second) == [
        ("success", "found"),
        ("failed", TOOL_LIMIT_MESSAGE),
    ]
    assert sorted(executed) == ["lookup", "search"]
    assert AbstractToolset.call_tool is original_call_tool


async def test_progress_shows_this_runs_tools_and_survives_update_errors():
    progress = SimpleNamespace(header="🔄 thinking", update=AsyncMock())
    watcher = ToolCallWatcher(
        progress=progress, task_settings={"task_run_name": "execute {tool_name}"}
    )

    async def search() -> str:
        return "found"

    agent = Agent(calls_then_answers("search", 2), tools=[search])
    await agent.run("hi", capabilities=[watcher.capability()])

    final = progress.update.call_args.args[0]
    assert final.startswith("🔄 thinking")
    assert "🔧 Using tool: `search`" in final
    assert "`search` (2x)" in final

    progress.update.side_effect = RuntimeError("slack is down")
    result = await agent.run("hi", capabilities=[watcher.capability()])
    assert result.output == "done"
