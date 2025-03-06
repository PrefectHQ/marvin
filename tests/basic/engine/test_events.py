from dataclasses import dataclass

from dirty_equals import IsPartialDataclass
from pydantic_ai.models.test import TestModel

import marvin
from marvin.handlers.handlers import Handler


class EventCollector(Handler):
    def __init__(self):
        self.events = []

    def on_event(self, event):
        self.events.append(event)


def my_tool(x: int) -> int:
    return x + 1


@dataclass
class Foo:
    x: int


def test_simple_events(test_model):
    collector = EventCollector()
    result = marvin.run(
        "",
        agents=[marvin.Agent(model=TestModel(custom_result_args={"result": {"x": 1}}))],
        result_type=Foo,
        handlers=[collector],
    )
    assert result == Foo(x=1)
    assert len(collector.events) == 7
    assert collector.events == [
        IsPartialDataclass(type="orchestrator-start"),
        IsPartialDataclass(type="actor-start-turn"),
        IsPartialDataclass(type="tool-call-delta"),
        IsPartialDataclass(type="end-turn-tool-call"),
        IsPartialDataclass(type="end-turn-tool-result"),
        IsPartialDataclass(type="actor-end-turn"),
        IsPartialDataclass(type="orchestrator-end"),
    ]


def test_tool_call_events(test_model):
    collector = EventCollector()
    result = marvin.run(
        "",
        agents=[marvin.Agent(model=TestModel(custom_result_args={"result": {"x": 1}}))],
        result_type=Foo,
        tools=[my_tool],
        handlers=[collector],
    )
    assert result == Foo(x=1)
    assert len(collector.events) == 10
    assert collector.events == [
        IsPartialDataclass(type="orchestrator-start"),
        IsPartialDataclass(type="actor-start-turn"),
        IsPartialDataclass(type="tool-call-delta"),
        IsPartialDataclass(type="tool-call"),
        IsPartialDataclass(type="tool-result"),
        IsPartialDataclass(type="tool-call-delta"),
        IsPartialDataclass(type="end-turn-tool-call"),
        IsPartialDataclass(type="end-turn-tool-result"),
        IsPartialDataclass(type="actor-end-turn"),
        IsPartialDataclass(type="orchestrator-end"),
    ]
