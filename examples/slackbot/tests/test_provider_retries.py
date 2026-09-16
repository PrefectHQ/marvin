import asyncio
from unittest.mock import AsyncMock

import pytest
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from slackbot._internal import retrying_model
from slackbot._internal.retrying_model import RetryingModel


async def test_retry_preserves_completed_tool_results(monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(retrying_model.asyncio, "sleep", sleep)
    requests = []
    tool_calls = []

    async def model(messages, info):
        requests.append(messages)
        if len(requests) == 1:
            return ModelResponse(parts=[ToolCallPart("lookup", {}, "call-1")])
        if len(requests) == 2:
            raise ModelHTTPError(503, "test", {"message": "overloaded"})
        return ModelResponse(parts=[TextPart("Here is the answer.")])

    def lookup() -> str:
        tool_calls.append(1)
        return "Verified result"

    agent = Agent(RetryingModel(FunctionModel(model)), tools=[lookup])
    result = await agent.run("Help me")
    assert result.output == "Here is the answer."
    assert len(tool_calls) == 1
    assert len(requests) == 3
    assert requests[1] is requests[2]
    sleep.assert_awaited_once_with(1)


@pytest.mark.parametrize(
    "status, attempts", [(503, 3), (429, 3), (529, 3), (401, 1), (400, 1)]
)
async def test_retry_budget_and_permanent_errors(monkeypatch, status, attempts):
    sleep = AsyncMock()
    monkeypatch.setattr(retrying_model.asyncio, "sleep", sleep)
    calls = []

    async def model(messages, info):
        calls.append(1)
        raise ModelHTTPError(status, "test", {"message": "provider detail"})

    with pytest.raises(ModelHTTPError):
        await Agent(RetryingModel(FunctionModel(model))).run("hello")
    assert len(calls) == attempts
    assert [call.args[0] for call in sleep.await_args_list] == (
        [1, 3] if attempts == 3 else []
    )


async def test_cancellation_during_backoff_propagates(monkeypatch):
    monkeypatch.setattr(
        retrying_model.asyncio, "sleep", AsyncMock(side_effect=asyncio.CancelledError)
    )
    calls = []

    async def model(messages, info):
        calls.append(1)
        raise ModelHTTPError(503, "test")

    with pytest.raises(asyncio.CancelledError):
        await Agent(RetryingModel(FunctionModel(model))).run("hello")
    assert len(calls) == 1
