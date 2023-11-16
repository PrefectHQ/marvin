import functools
from contextlib import contextmanager
from enum import Enum, auto
from typing import Any, Callable, Generic, Optional, TypeVar

from prefect import flow as prefect_flow
from prefect import task as prefect_task
from pydantic import BaseModel, Field
from rich.prompt import Prompt
from typing_extensions import ParamSpec

from marvin.beta.assistants import Assistant, Run, Thread
from marvin.beta.assistants.formatting import pprint_message, pprint_messages
from marvin.beta.assistants.runs import CancelRun
from marvin.serializers import create_tool_from_type
from marvin.tools.assistants import AssistantTools
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
appear unrelated to the current task. Each task will be part of a continuous
conversation, so do not continue to reintroduce yourself each time.

Note: Sometimes you will be able to complete a task without user input; other
times you will need to engage the user in conversation. Pay attention to your
instructions.


## Progress
{% for task in tasks -%}
- {{ task.name }}: {{ task.status }}
{% endfor %}}}

# Task

## Current task

Your job is to complete the "{{ name }}" task.

## Current task instructions

{{ instructions }}

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
a string describing why the task failed.

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
    tools: list[AssistantTools] = []
    max_run_iterations: int = 15
    result: Optional[T] = None

    def __call__(self, *args: P.args, _thread_id: str = None, **kwargs: P.kwargs) -> T:
        if _thread_id is None:
            _thread_id = thread_context.get("thread_id")

        ptask = prefect_task(name=self.name)(self.call)

        return ptask(*args, _thread_id=_thread_id, **kwargs)

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

                if iterations > 1:
                    user_input = Prompt.ask("Your message")
                    msg = thread.add(user_input)
                    pprint_message(msg)
                else:
                    msg = None

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

                messages = thread.get_messages(after_message=msg.id if msg else None)
                pprint_messages(messages)

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
            first_message=(iterations == 1),
            name=self.name,
            instructions=self.instructions,
            func=self.fn,
            args=args,
            kwargs=kwargs,
        )

    @property
    def _task_completed_tool(self):
        tool = create_tool_from_type(
            _type=self.fn.__annotations__["return"],
            model_name="task_completed",
            model_description=(
                "Indicate that the task completed and produced the provided `result`."
            ),
            field_name="result",
            field_description="The task result",
        )

        def task_completed(result: T):
            self.status = Status.COMPLETED
            self.result = result
            raise CancelRun()

        tool.function.python_fn = task_completed

        return tool

    @property
    def _task_failed_tool(self):
        def task_failed(reason: str) -> None:
            """Indicate that the task failed for the provided `reason`."""
            self.status = Status.FAILED
            self.result = reason
            raise CancelRun()

        return tool_from_function(task_failed)


def ai_task(*args, name=None, instructions=None, tools: list[AssistantTools] = None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*func_args, **func_kwargs):
            ai_task_instance = AITask(
                fn=func,
                name=name or func.__name__,
                instructions=instructions or func.__doc__,
                tools=tools or [],
            )
            return ai_task_instance(*func_args, **func_kwargs)

        return wrapper

    if args and callable(args[0]):
        return decorator(args[0])

    return decorator


@contextmanager
def ai_flow_context(thread_id: str = None, tasks: list[AITask] = None, **kwargs):
    # create a new thread for the flow
    thread = Thread(id=thread_id)
    if thread_id is None:
        thread.create()

    # create a holder for the tasks
    tasks = tasks or []

    # enter the thread context
    with thread_context(thread_id=thread.id, tasks=tasks, **kwargs):
        yield


class AIFlow(BaseModel):
    name: Optional[str] = None
    fn: Callable

    def __call__(self, *args, **kwargs):
        pflow = prefect_flow(name=self.name)(self.fn)
        # Set up the thread context and execute the flow
        with ai_flow_context():
            return pflow(*args, **kwargs)


def ai_flow(*args, name=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*func_args, **func_kwargs):
            ai_flow_instance = AIFlow(fn=func, name=name or func.__name__)
            return ai_flow_instance(*func_args, **func_kwargs)

        return wrapper

    if args and callable(args[0]):
        return decorator(args[0])

    return decorator
