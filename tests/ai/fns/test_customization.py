from functools import partial
from typing import Any, Callable

import pytest

import marvin
from marvin.engine.events import Event
from marvin.handlers.queue_handler import QueueHandler


class TestCustomHandlers:
    @pytest.fixture
    def collector(self):
        class FooQueueHandler(QueueHandler):
            # a convenience class convenient for asserts in testing
            def __init__(self):
                super().__init__()
                self.seen_events: list[Event] = []

            async def on_event(self, event: Event):
                self.seen_events.append(event)

        return FooQueueHandler()

    @pytest.mark.usefixtures("test_model")
    @pytest.mark.parametrize(
        "func, args",
        [
            (marvin.summarize, ("Brexit in 4 words",)),
            (marvin.cast, ("answer to it all", int)),
            (marvin.extract, ("i got 99 problems", int)),
            (marvin.generate, (int, 3)),
            (marvin.say, ("hi",)),
        ],
        ids=["summarize", "cast", "extract", "generate", "say"],
    )
    def test_fns_handlers_passthrough(
        self,
        func: Callable[..., Any],
        args: tuple[Any, ...],
        collector: Any,
    ):
        partial(func, handlers=[collector])(*args)
        assert len(collector.seen_events) > 0


class TestCustomPrompt:
    @pytest.mark.usefixtures("gpt_4o")
    def test_custom_prompt(self):
        @marvin.fn(prompt="expertly predict output of this function, use ALL CAPS!")
        def genie(hint: str) -> str:
            """tell me the answer mr genie sir"""

        llm_guess = genie("the last name of the first US president")
        assert llm_guess == "WASHINGTON", f"expected WASHINGTON, got {llm_guess}"
