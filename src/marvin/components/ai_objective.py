import functools
from enum import Enum, auto
from typing import Any, Callable, Generic, Optional, TypeVar

from pydantic import BaseModel, Field
from rich.prompt import Prompt
from typing_extensions import ParamSpec

from marvin.beta.assistants import Assistant, Run, Thread
from marvin.beta.assistants.formatting import pprint_message, pprint_messages
from marvin.beta.assistants.runs import CancelRun
from marvin.serializers import create_tool_from_type
from marvin.tools.assistants import AssistantTools
from marvin.utilities.asyncio import run_sync
from marvin.utilities.jinja import Environment as JinjaEnvironment
from marvin.utilities.tools import tool_from_function

T = TypeVar("T", bound=BaseModel)

P = ParamSpec("P")


INSTRUCTIONS = """
# Current task

You are currently working on the "{{ name }}" task. Complete the task in
accordance with the description below.

# Task description

{{ instructions }}

{% if first_message -%}
# No user input

If there is no user input, that's because the user doesn't know about the task
yet. You should send a message to the user to get them to respond.

{% endif %}

# Completing the task

After achieving your goal, you MUST call the `task_completed` tool to mark the
task as complete and move on to the next one. The payload to `task_completed` is
whatever information represents the task objective. For example, if your task is
to learn a user's name, you should respond with their properly formatted name
only.

You may be expected to return a
specific data payload at the end of your task, which will be the input to
`task_completed`. Note that if your instructions are to talk to the user, then
you must do so by creating messages, as the user can not see the `task_completed`
tool result.

Do not call `task_completed` unless you actually have the information you need.
The user CAN NOT see what you post to `task_completed`. It is not a way to
communicate with the user.

# Failing the task

It may take you a few tries to complete the task. However, if you are ultimately
unable to work with the user to complete it, call the `task_failed` tool to mark
the task as failed and move on to the next one. The payload to `task_failed` is
a string describing why the task failed.

{% if args or kwargs -%}
# Task inputs

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


class ObjectiveStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


class AIObjective(BaseModel, Generic[P, T]):
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    fn: Callable[P, Any]
    name: str = Field(None, description="The name of the objective")
    instructions: str = Field(None, description="The instructions for the objective")
    assistant: Optional[Assistant] = None
    tools: list[AssistantTools] = []
    max_run_iterations: int = 15
    result: Optional[T] = None

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return run_sync(self.call(*args, **kwargs))

    async def call(self, *args, _thread_id: str = None, **kwargs):
        thread = Thread(id=_thread_id)
        if _thread_id is None:
            thread.create()
        iterations = 0

        self.status = ObjectiveStatus.IN_PROGRESS

        with Assistant() as assistant:
            while self.status == ObjectiveStatus.IN_PROGRESS:
                iterations += 1
                if iterations > self.max_run_iterations:
                    raise ValueError("Max run iterations exceeded")

                instructions = self.get_instructions(
                    iterations=iterations, *args, **kwargs
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

            if self.status == ObjectiveStatus.FAILED:
                raise ValueError(f"Objective failed: {self.result}")

        return self.result

    def get_instructions(
        self, iterations: int, *args: P.args, **kwargs: P.kwargs
    ) -> str:
        return JinjaEnvironment.render(
            INSTRUCTIONS,
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
                "Use this tool to complete the objective and provide a result that"
                " contains its result."
            ),
            field_name="result",
            field_description="The objective result",
        )

        def task_completed(result: T):
            self.status = ObjectiveStatus.COMPLETED
            self.result = result
            return "The task is complete. Do NOT continue talking at this time."

        tool.function.python_fn = task_completed

        return tool

    @property
    def _task_failed_tool(self):
        def task_failed(reason: str) -> None:
            """Indicate that the task failed for the provided `reason`."""
            self.status = ObjectiveStatus.FAILED
            self.result = reason
            raise CancelRun()

        return tool_from_function(task_failed)


def ai_objective(
    *args, name=None, instructions=None, tools: list[AssistantTools] = None
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*func_args, **func_kwargs):
            ai_objective_instance = AIObjective(
                fn=func,
                name=name or func.__name__,
                instructions=instructions or func.__doc__,
                tools=tools or [],
            )
            return ai_objective_instance(*func_args, **func_kwargs)

        return wrapper

    if args and callable(args[0]):
        return decorator(args[0])

    return decorator
