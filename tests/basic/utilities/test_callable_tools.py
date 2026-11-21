import inspect

import pytest
from pydantic_ai import ModelRetry
from pydantic_ai.models.test import TestModel

from marvin import Agent
from marvin.utilities.tools import update_fn, wrap_tool_errors


class Lookup:
    def __init__(self):
        self.calls = 0

    def __call__(self, query: str) -> str:
        """Look up an item by query."""
        self.calls += 1
        if self.calls == 1:
            raise ValueError("temporary lookup failure")
        return query


class AsyncLookup(Lookup):
    async def __call__(self, query: str) -> str:
        """Look up an item asynchronously."""
        return super().__call__(query)


@pytest.mark.parametrize("lookup_type", [Lookup, AsyncLookup])
@pytest.mark.parametrize("rename", [False, True])
async def test_callable_tool_runs_and_retries(lookup_type, rename):
    lookup = lookup_type()
    tool = update_fn(lookup, name="lookup") if rename else lookup
    agent = Agent(tools=[tool], model=TestModel())

    agentlet = await agent.get_agentlet(tools=[], end_turn_tools=[])
    await agentlet.run("Look up an item")

    assert lookup.calls == 2


async def test_async_callable_errors_become_model_retries():
    wrapped = wrap_tool_errors(AsyncLookup())
    with pytest.raises(ModelRetry, match="temporary lookup failure"):
        await wrapped("item")


def test_update_fn_preserves_callable_annotations():
    lookup = Lookup()
    updated = update_fn(lookup, name="lookup")
    assert updated.__annotations__ == lookup.__call__.__annotations__
    assert inspect.signature(updated) == inspect.signature(lookup)


def test_update_fn_preserves_async_callable_kind():
    updated = update_fn(AsyncLookup(), name="lookup")
    assert inspect.iscoroutinefunction(updated)
