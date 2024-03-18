from openai import AsyncAssistantEventHandler
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import RunStep, RunStepDelta, ToolCall
from rich.console import Group
from rich.live import Live
from typing_extensions import override

from marvin.beta.assistants.formatting import format_run


class RunHandler(AsyncAssistantEventHandler):
    def __init__(
        self,
        steps: list[RunStep] = None,
        messages: list[Message] = None,
        live: Live = None,
        print: bool = True,
    ):
        self._messages = {m.id: m for m in messages or []}
        self._steps = {s.id: s for s in steps or []}
        self.print = print
        self.live = live or Live(refresh_per_second=15)
        if self.print:
            self.live.start()
        super().__init__()

    @property
    def messages(self):
        return sorted(self._messages.values(), key=lambda m: m.created_at)

    @property
    def steps(self):
        return sorted(self._steps.values(), key=lambda s: s.created_at)

    def print_run(self):
        panels = format_run(self)
        self.live.update(Group(*panels))

    @override
    async def on_message_delta(self, delta: MessageDelta, snapshot: Message) -> None:
        self._messages[snapshot.id] = snapshot
        if self.print:
            self.print_run()

    @override
    async def on_message_done(self, message: Message) -> None:
        self._messages[message.id] = message
        if self.print:
            self.print_run()

    @override
    async def on_run_step_delta(self, delta: RunStepDelta, snapshot: RunStep) -> None:
        self._steps[snapshot.id] = snapshot
        if self.print:
            self.print_run()

    @override
    async def on_run_step_done(self, run_step: RunStep) -> None:
        self._steps[run_step.id] = run_step
        if self.print:
            self.print_run()

    @override
    async def on_exception(self, exc):
        if self.print:
            self.live.stop()

    @override
    async def on_end(self):
        if self.print:
            self.live.stop()

    @override
    async def on_tool_call_done(self, tool_call: ToolCall) -> None:
        pass
