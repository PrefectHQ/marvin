import asyncio

import pytest
from pydantic_ai.messages import UserPromptPart

from marvin.engine.events import Event, ToolRetryEvent, UserMessageEvent
from marvin.handlers import QueueHandler


@pytest.mark.parametrize(
    "include, expected",
    [
        (None, True),
        ([UserMessageEvent], True),
        (["user-message"], True),
        ([ToolRetryEvent, "user-message"], True),
        (["tool-retry", UserMessageEvent], True),
        (["tool-retry"], False),
        ([ToolRetryEvent], False),
    ],
)
async def test_include_matches_event_class_or_type(
    include: list[str | type[Event]] | None, expected: bool
) -> None:
    queue: asyncio.Queue[Event] = asyncio.Queue()
    handler = QueueHandler(queue=queue, include=include)
    event = UserMessageEvent(message=UserPromptPart(content="hello"))

    await handler.on_event(event)

    assert queue.qsize() == int(expected)
    if expected:
        assert queue.get_nowait() is event


@pytest.mark.parametrize("exclude", [[UserMessageEvent], ["user-message"]])
async def test_exclude_overrides_matching_include(
    exclude: list[str | type[Event]],
) -> None:
    handler = QueueHandler(include=[UserMessageEvent, "user-message"], exclude=exclude)

    await handler.on_event(UserMessageEvent(message=UserPromptPart(content="hello")))

    assert handler.queue.empty()
