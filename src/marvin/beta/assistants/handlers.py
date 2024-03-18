from openai import AssistantEventHandler, AsyncAssistantEventHandler
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import RunStep, RunStepDelta
from rich.console import Group
from rich.live import Live
from typing_extensions import override

from marvin.beta.assistants.formatting import format_run


class RunHandler(AssistantEventHandler):
    def get_final_messages(self):
        # this errors if no messages were generated, which can happen
        # when making tool calls
        try:
            return super().get_final_messages()
        except RuntimeError:
            return []

    def get_final_run_steps(self):
        # this errors if no run_steps were generated, which can happen
        # when making tool calls
        try:
            return super().get_final_run_steps()
        except RuntimeError:
            return []


class AsyncRunHandler(AsyncAssistantEventHandler):
    async def get_final_messages(self):
        # this errors if no messages were generated, which can happen
        # when making tool calls
        try:
            return await super().get_final_messages()
        except RuntimeError:
            return []

    async def get_final_run_steps(self):
        # this errors if no run_steps were generated, which can happen
        # when making tool calls
        try:
            return await super().get_final_run_steps()
        except RuntimeError:
            return []


class PrintRunHandler(AsyncRunHandler):
    def __init__(self):
        self._messages = {}
        self._steps = {}
        self.live = Live(refresh_per_second=15)
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
        self.print_run()

    @override
    async def on_message_done(self, message: Message) -> None:
        self._messages[message.id] = message
        self.print_run()

    @override
    async def on_run_step_delta(self, delta: RunStepDelta, snapshot: RunStep) -> None:
        self._steps[snapshot.id] = snapshot
        self.print_run()

    @override
    async def on_run_step_done(self, run_step: RunStep) -> None:
        self._steps[run_step.id] = run_step
        self.print_run()

    @override
    async def on_exception(self, exc):
        self.live.stop()

    @override
    async def on_end(self):
        self.live.stop()
