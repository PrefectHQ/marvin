from openai import AsyncAssistantEventHandler
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import RunStep, RunStepDelta
from rich.console import Group
from rich.live import Live
from typing_extensions import override

from marvin.beta.assistants.formatting import format_run


class PrintHandler(AsyncAssistantEventHandler):
    def __init__(self, print_messages: bool = True, print_steps: bool = True):
        self.print_messages = print_messages
        self.print_steps = print_steps
        self.live = Live(refresh_per_second=12)
        self.live.start()
        self.messages = {}
        self.steps = {}
        super().__init__()

    def print_run(self):
        class Run:
            messages = self.messages.values()
            steps = self.steps.values()

        panels = format_run(
            Run,
            include_messages=self.print_messages,
            include_steps=self.print_steps,
        )
        self.live.update(Group(*panels))

    @override
    async def on_message_delta(self, delta: MessageDelta, snapshot: Message) -> None:
        self.messages[snapshot.id] = snapshot
        self.print_run()

    @override
    async def on_message_done(self, message: Message) -> None:
        self.messages[message.id] = message
        self.print_run()

    @override
    async def on_run_step_delta(self, delta: RunStepDelta, snapshot: RunStep) -> None:
        self.steps[snapshot.id] = snapshot
        self.print_run()

    @override
    async def on_run_step_done(self, run_step: RunStep) -> None:
        self.steps[run_step.id] = run_step
        self.print_run()

    @override
    async def on_exception(self, exc):
        self.live.stop()

    @override
    async def on_end(self):
        self.live.stop()
