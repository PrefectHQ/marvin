from openai import AsyncAssistantEventHandler
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import RunStep, RunStepDelta
from rich.console import Group
from rich.live import Live
from typing_extensions import override

from marvin.beta.assistants.formatting import format_run

# class MarvinHandler(AsyncAssistantEventHandler):
#     """
#     A container that composes multiple AssistantEventHandlers or
#     AsyncAssistantEventHandlers into a single object by delegating the on_*
#     methods to each handler.
#     """

#     def __init__(self, handlers: list[AssistantEventHandler] = None):
#         self.handlers = handlers or []
#         super().__init__()

#     # def __setattr__(self, name, value):
#     #     # Set the attribute on the RunHandler instance
#     #     super().__setattr__(name, value)

#     #     # Also set the attribute on each handler
#     #     for handler in self.handlers:
#     #         setattr(handler, name, value)

#     def __getattribute__(self, name):
#         parent_attr = super().__getattribute__(name)

#         # Check if the method starts with 'on_'
#         if name.startswith("on_")

#             # if it does, return a special method that calls the equivalent method
#             # on each handler (accounting for async methods)
#             async def _on_event_method(*args, **kwargs):
#                 await parent_attr(*args, **kwargs)
#                 for handler in self.handlers:
#                     method = getattr(handler, name)
#                     result = method(*args, **kwargs)
#                     if inspect.iscoroutine(result):
#                         await result

#             return _on_event_method

#         else:
#             # Otherwise, access the RunHandler's true attribute
#             return parent_attr

#     async def get_final_messages(self):
#         # this errors if no messages were generated, which can happen
#         # when making tool calls
#         try:
#             return await super().get_final_messages()
#         except RuntimeError:
#             return []

#     async def get_final_run_steps(self):
#         # this errors if no run_steps were generated, which can happen
#         # when making tool calls
#         try:
#             return await super().get_final_run_steps()
#         except RuntimeError:
#             return []


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
