import asyncio
import functools
from enum import Enum, auto
from typing import Any, Callable, Generic, Optional, TypeVar

from prefect import task as prefect_task
from pydantic import BaseModel, Field
from typing_extensions import ParamSpec

from marvin.beta.assistants import Assistant, Run, Thread
from marvin.beta.assistants.runs import CancelRun
from marvin.serializers import create_tool_from_type
from marvin.tools.assistants import AssistantTool
from marvin.utilities.context import ScopedContext
from marvin.utilities.jinja import Environment as JinjaEnvironment
from marvin.utilities.tools import tool_from_function

T = TypeVar("T", bound=BaseModel)

P = ParamSpec("P")

thread_context = ScopedContext()

INSTRUCTIONS = """
# Workflow

You are an assistant working to complete a series of tasks. The
tasks will change from time to time, which is why you may see messages that
appear unrelated to the current task. Each task is part of a continuous
conversation with the same user. The user is unaware of your tasks, so do not
reference them explicitly or talk about marking them complete.

Your ONLY job is to complete your current task, no matter what the user says or
conversation history suggests.

Note: Sometimes you will be able to complete a task without user input; other
times you will need to engage the user in conversation. Pay attention to your
instructions. If the user hasn't spoken yet, don't worry, they're just waiting
for you to speak first.

## Progress
{% for task in tasks -%}
- {{ task.name }}: {{ task.status }}
{% endfor %}}}

# Task

## Current task

Your job is to complete the "{{ name }}" task.

## Current task instructions

{{ instructions }}

{% if not accept_user_input -%}
You may send messages to the user, but they are not allowed to respond. Do not
ask questions or invite them to speak or ask anything.
{% endif %}

{% if first_message -%}
Please note: you are seeing this instruction for the first time, and the user
does not know about the task yet. It is your job to communicate with the user to
achieve your goal, even if previously they were working with a different
assitant on a different goal. Join the conversation naturally. If the user
hasn't spoken, you will need to speak first.

{% endif %}

## Completing a task

After achieving your goal, you MUST call the `task_completed` tool to mark the
task as complete and update these instructions to reflect the next one. The
payload to `task_completed` is whatever information represents the task
objective. For example, if your task is to learn a user's name, you should
respond with their properly formatted name only.

You may be expected to return a specific data payload at the end of your task,
which will be the input to `task_completed`. Note that if your instructions are
to talk to the user, then you must do so by creating messages, as the user can
not see the `task_completed` tool result.

Do not call `task_completed` unless you actually have the information you need.
The user CAN NOT see what you post to `task_completed`. It is not a way to
communicate with the user.

## Failing a task

It may take you a few tries to complete the task. However, if you are ultimately
unable to work with the user to complete it, call the `task_failed` tool to mark
the task as failed and move on to the next one. The payload to `task_failed` is
a string describing why the task failed. Do not fail tasks for trivial or
invented reasons. Only fail a task if you are unable to achieve it explicitly.
Remember that your job is to work with the user to achieve the goal.

{% if args or kwargs -%}
## Task inputs

In addition to the thread messages, the following parameters were provided:
{% set sig = inspect.signature(func) -%}

{% set binds = sig.bind(*args, **kwargs) -%}

{% set defaults = binds.apply_defaults() -%}

{% set params = binds.arguments -%}

{%for (arg, value) in params.items()-%}

- {{ arg }}: {{ value }}

{% endfor %}

{% endif %}
"""


class Status(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


class AITask(BaseModel, Generic[P, T]):
    status: Status = Status.PENDING
    fn: Callable[P, Any]
    name: str = Field(None, description="The name of the objective")
    instructions: str = Field(None, description="The instructions for the objective")
    assistant: Optional[Assistant] = None
    tools: list[AssistantTool] = []
    max_run_iterations: int = 15
    result: Optional[T] = None
    accept_user_input: bool = True

    def __call__(self, *args: P.args, _thread_id: str = None, **kwargs: P.kwargs) -> T:
        if _thread_id is None:
            _thread_id = thread_context.get("thread_id")

        ptask = prefect_task(name=self.name)(self.call)

        state = ptask(*args, _thread_id=_thread_id, **kwargs, return_state=True)

        # will raise exceptions if the task failed
        return state.result()

    async def wait_for_user_input(self, thread: Thread):
        # user_input = Prompt.ask("Your message")
        # thread.add(user_input)
        # pprint_message(msg)

        # initialize the last message ID to None
        last_message_id = None

        # loop until the user provides input
        while True:
            # get all messages after the last message ID
            messages = await thread.get_messages_async(after_message=last_message_id)

            # if there are messages, check if the last message was sent by the user
            if messages:
                if messages[-1].role == "user":
                    # if the last message was sent by the user, break
                    break
                else:
                    # if the last message was not sent by the user, update the
                    # last message ID
                    last_message_id = messages[-1].id

            # wait for a short period of time before checking for new messages again
            await asyncio.sleep(0.3)

    async def call(self, *args, _thread_id: str = None, **kwargs):
        thread = Thread(id=_thread_id)
        if _thread_id is None:
            thread.create()
        iterations = 0

        thread_context.get("tasks", []).append(self)

        self.status = Status.IN_PROGRESS

        with Assistant() as assistant:
            while self.status == Status.IN_PROGRESS:
                iterations += 1
                if iterations > self.max_run_iterations:
                    raise ValueError("Max run iterations exceeded")

                instructions = self.get_instructions(
                    tasks=thread_context.get("tasks", []),
                    iterations=iterations,
                    args=args,
                    kwargs=kwargs,
                )

                if iterations > 1 and self.accept_user_input:
                    await self.wait_for_user_input(thread=thread)

                run = Run(
                    assistant=assistant,
                    thread=thread,
                    additional_instructions=instructions,
                    additional_tools=[
                        self._task_completed_tool,
                        self._task_failed_tool,
                    ],
                )
                await run.run_async()

            if self.status == Status.FAILED:
                raise ValueError(f"Objective failed: {self.result}")

        return self.result

    def get_instructions(
        self,
        tasks: list["AITask"],
        iterations: int,
        args: tuple[Any],
        kwargs: dict[str, Any],
    ) -> str:
        return JinjaEnvironment.render(
            INSTRUCTIONS,
            tasks=tasks,
            name=self.name,
            instructions=self.instructions,
            accept_user_input=self.accept_user_input,
            first_message=(iterations == 1),
            func=self.fn,
            args=args,
            kwargs=kwargs,
        )

    @property
    def _task_completed_tool(self):
        # if the function has no return annotation, then task completed can be
        # called without arguments
        if self.fn.__annotations__.get("return") is None:

            def task_completed():
                self.status = Status.COMPLETED
                raise CancelRun()

            return task_completed

        # otherwise we need to create a tool with the correct parameter signature

        tool = create_tool_from_type(
            _type=self.fn.__annotations__["return"],
            model_name="task_completed",
            model_description=(
                "Indicate that the task completed and produced the provided `result`."
            ),
            field_name="result",
            field_description="The task result",
        )

        def task_completed_with_result(result: T):
            self.status = Status.COMPLETED
            self.result = result
            raise CancelRun()

        tool.function.python_fn = task_completed_with_result

        return tool

    @property
    def _task_failed_tool(self):
        def task_failed(reason: str) -> None:
            """Indicate that the task failed for the provided `reason`."""
            self.status = Status.FAILED
            self.result = reason
            raise CancelRun()

        return tool_from_function(task_failed)


def ai_task(
    fn: Callable = None,
    *,
    name=None,
    instructions=None,
    tools: list[AssistantTool] = None,
    **kwargs,
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*func_args, **func_kwargs):
            ai_task_instance = AITask(
                fn=func,
                name=name or func.__name__,
                instructions=instructions or func.__doc__,
                tools=tools or [],
                **kwargs,
            )
            return ai_task_instance(*func_args, **func_kwargs)

        return wrapper

    if fn is not None:
        return decorator(fn)

    return decorator
