import inspect
from enum import Enum
from typing import Any, Callable, Optional, Union

from jsonpatch import JsonPatch
from pydantic import BaseModel, Field, validator

import marvin
from marvin._compat import PYDANTIC_V2, model_dump
from marvin.core.ChatCompletion.providers.openai import get_context_size
from marvin.openai import ChatCompletion
from marvin.prompts import library as prompt_library
from marvin.prompts.base import Prompt, render_prompts
from marvin.tools import Tool
from marvin.utilities.async_utils import run_sync
from marvin.utilities.history import History
from marvin.utilities.messages import Message, Role
from marvin.utilities.types import LoggerMixin, MarvinBaseModel

SYSTEM_PROMPT = """
    # Overview

    You are the intelligent, natural language interface to an application. The
    application has a structured `state` but no formal API; you are the only way
    to interact with it. You must interpret the user's inputs as attempts to
    interact with the application's state in the context of the application's
    purpose. For example, if the application is a to-do tracker, then "I need to
    go to the store" should be interpreted as an attempt to add a new to-do
    item. If it is a route planner, then "I need to go to the store" should be
    interpreted as an attempt to find a route to the store.

    # Actions

    Each time the user runs the application by sending a message, you must take
    the following steps:

    {% if app.plan_enabled %}

    - Call the `update_plan` function to update your plan. Use your plan
    to track notes, objectives, in-progress work, and to break problems down
    into solvable, possibly dependent parts. You plan consists of a few fields:

        - `notes`: a list of notes you have taken. Notes are free-form text and
        can be used to track anything you want to remember, such as
        long-standing user instructions, or observations about how to behave or
        operate the application. Your notes should always impact your behavior.
        These are exclusively related to your role as intermediary and you
        interact with the user and application. Do not track application data or
        state here.

        - `tasks`: a list of tasks you are working on. Tasks track goals,
        milestones, in-progress work, and break problems down into all the
        discrete steps needed to solve them. You should create a new task for
        any work that will require a function call other than updating state, or
        will require more than one state update to complete. You do not need to
        create tasks for simple state updates. Use optional parent tasks to
        indicate nested relationships; parent tasks are not completed until all
        their children are complete. Use optional upstream tasks to indicate
        dependencies; a task can not be completed until its upstream tasks are
        completed.

    {% endif %}

    - Call any functions necessary to achieve the application's purpose.

    {% if app.state_enabled %}

    - Call the `update_state` function to update the application's state. This
    is where you should store any information relevant to the application
    itself.

    {% endif %}

    You can call these functions at any time, in any order, as necessary.
    Finally, respond to the user with an informative message. Remember that the
    user is probably uninterested in the internal steps you took, so respond
    only in a manner appropriate to the application's purpose.

    # Application details

    ## Name

    {{ app.name }}

    ## Description

    {{ app.description or '' | render }}

    {% if app.state_enabled %}

    ## Application state

    {{ app.state.json() }}

    ### Application state schema

    {{ app.state.schema_json() }}

    {% endif %}

    {%- if app.plan_enabled %}

    ## Your current plan

    {{ app.plan.json() }}

    ### Your plan schema

    {{ app.plan.schema_json() }}

    {%- endif %}
    """


class TaskState(Enum):
    """The state of a task.

    Attributes:
        PENDING: The task is pending and has not yet started.
        IN_PROGRESS: The task is in progress.
        COMPLETED: The task is completed.
        FAILED: The task failed.
        SKIPPED: The task was skipped.
    """

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Task(BaseModel):
    class Config:
        validate_assignment = True

    id: int
    description: str
    upstream_task_ids: Optional[list[int]] = None
    parent_task_id: Optional[int] = None
    state: TaskState = TaskState.IN_PROGRESS


class AppPlan(BaseModel):
    """The AI's plan in service of the application.

    Attributes:
        tasks: A list of tasks the AI is working on.
        notes: A list of notes the AI has taken.
    """

    tasks: list[Task] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class FreeformState(BaseModel):
    """A freeform state object that can be used to store any JSON-serializable data.

    Attributes:
        state: The state object.
    """

    state: dict[str, Any] = Field(default_factory=dict)


class AIApplication(LoggerMixin, MarvinBaseModel):
    """An AI application is a stateful, autonomous, natural language
        interface to an application.

    Attributes:
        name: The name of the application.
        description: A description of the application.
        state: The application's state - this can be any JSON-serializable object.
        plan: The AI's plan in service of the application - this can be any
            JSON-serializable object.
        tools: A list of tools that the AI can use to interact with
            application or outside world.
        history: A history of all messages sent and received by the AI.
        additional_prompts: A list of additional prompts that will be
            added to the prompt stack for rendering.

    Example:
        Create a simple todo app where AI manages its own state and plan.
        ```python
        from marvin import AIApplication

        todo_app = AIApplication(
            name="Todo App",
            description="A simple todo app.",
        )

        todo_app("I need to go to the store.")

        print(todo_app.state, todo_app.plan)
        ```
    """

    name: Optional[str] = None
    description: Optional[str] = None
    state: BaseModel = Field(default_factory=FreeformState)
    plan: AppPlan = Field(default_factory=AppPlan)
    tools: list[Union[Tool, Callable[..., Any]]] = Field(default_factory=list)
    history: History = Field(default_factory=History)
    additional_prompts: list[Prompt] = Field(
        default_factory=list,
        description=(
            "Additional prompts that will be added to the prompt stack for rendering."
        ),
    )
    stream_handler: Optional[Callable[[Message], None]] = None
    state_enabled: bool = False
    plan_enabled: bool = False

    @validator("description")
    def validate_description(cls, v):
        return inspect.cleandoc(v)

    @validator("additional_prompts")
    def validate_additional_prompts(cls, v):
        if v is None:
            v = []
        return v

    @validator("tools", pre=True, always=True)
    def validate_tools(cls, v):
        if v is None:
            v = []

        tools = []

        # convert AI Applications and functions to tools
        for tool in v:
            if isinstance(tool, (AIApplication, Tool)):
                tools.append(tool.as_function(description=tool.description))
            elif callable(tool):
                tools.append(tool)
            else:
                raise ValueError(f"Tool {tool} is not a `Tool` or callable.")
        return tools

    @validator("name", always=True)
    def validate_name(cls, v):
        if v is None:
            v = cls.__name__
        return v

    def __call__(self, input_text: str = None, model: str = None, tools: list[Tool] = None, extra_prompts: list[Prompt] = [], request_handler: Callable = None, response_handler: Callable = None, **model_kwargs):
        return run_sync(self.run(
            input_text=input_text, 
            model=model, 
            tools=tools, 
            extra_prompts=extra_prompts, 
            request_handler=request_handler,
            response_handler=response_handler,
            **model_kwargs
        ))

    async def entrypoint(self, q: str) -> str:
        response = await self.run(input_text=q)
        return response.content

    async def run(self, input_text: str = None, model: str = None, tools: list[Tool] = None, extra_prompts: list[Prompt] = [], request_handler: Callable = None, response_handler: Callable = None, **model_kwargs) -> Message:
        if model is None:
            model = marvin.settings.llm_model or "openai/gpt-4"

        # set up prompts
        prompts = [
            # system prompts
            prompt_library.System(content=SYSTEM_PROMPT),
            # add current datetime
            prompt_library.Now(),
            *self.additional_prompts,
            *extra_prompts,
            # get the history of messages between user and assistant
            prompt_library.MessageHistory(history=self.history),
        ]

        # get latest user input
        input_text = input_text or ""
        self.logger.debug_kv("User input", input_text, key_style="green")
        self.history.add_message(Message(content=input_text, role=Role.USER))


        max_tokens = get_context_size(model=model)
        self.logger.debug_kv("Model", model, key_style="blue")
        self.logger.debug_kv("Max tokens", max_tokens,key_style="blue")
        message_list = render_prompts(
            prompts=prompts,
            render_kwargs=dict(app=self, input_text=input_text),
            max_tokens=max_tokens,
        )

        # set up tools
        if tools:
            tools = self.validate_tools(tools)
        else:
            tools = self.tools

        tools = tools.copy()

        if self.state_enabled:
            tools.append(UpdateState(app=self).as_function())
        if self.plan_enabled:
            tools.append(UpdatePlan(app=self).as_function())

        conversation = await ChatCompletion(
            model=model,
            functions=tools,
            stream_handler=self.stream_handler,
            request_handler=request_handler,
            response_handler=response_handler,
            **model_kwargs,
        ).achain(messages=message_list)

        last_message = conversation.history[-1]

        # add the AI's response to the history
        self.history.add_message(last_message)

        self.logger.debug_kv("AI response", last_message.content, key_style="blue")
        return last_message

    def as_tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tool:
        return AIApplicationTool(app=self, name=name, description=description)

    def as_function(self, name: str = None, description: str = None) -> Callable:
        return self.as_tool(name=name, description=description).as_function()


class AIApplicationTool(Tool):
    app: "AIApplication"

    def __init__(self, **kwargs):
        if "name" not in kwargs:
            kwargs["name"] = type(self.app).__name__
        super().__init__(**kwargs)

    def run(self, input_text: str) -> str:
        return run_sync(self.app.run(input_text))


class JSONPatchModel(
    BaseModel,
    **(
        {
            "allow_population_by_field_name": True,
        }
        if not PYDANTIC_V2
        else {
            "populate_by_name": True,
        }
    ),
):
    """A JSON Patch document.

    Attributes:
        op: The operation to perform.
        path: The path to the value to update.
        value: The value to update the path to.
        from_: The path to the value to copy from.
    """

    op: str
    path: str
    value: Union[str, float, int, bool, list, dict] = None
    from_: str = Field(None, alias="from")


class UpdateState(Tool):
    """A `Tool` that updates the apps state using JSON Patch documents."""

    app: "AIApplication" = Field(..., repr=False, exclude=True)
    description: str = """
        Update the application state by providing a list of JSON patch
        documents. The state must always comply with the state's
        JSON schema.
        """

    def __init__(self, app: AIApplication, **kwargs):
        super().__init__(**kwargs, app=app)

    def run(self, patches: list[JSONPatchModel]):
        patch = JsonPatch(patches)
        updated_state = patch.apply(model_dump(self.app.state))
        self.app.state = type(self.app.state)(**updated_state)
        return "Application state updated successfully!"


class UpdatePlan(Tool):
    """A `Tool` that updates the apps plan using JSON Patch documents."""

    app: "AIApplication" = Field(..., repr=False, exclude=True)
    description: str = """
        Update the application plan by providing a list of JSON patch
        documents. The state must always comply with the plan's JSON schema.
        """

    def __init__(self, app: AIApplication, **kwargs):
        super().__init__(**kwargs, app=app)

    def run(self, patches: list[JSONPatchModel]):
        patch = JsonPatch(patches)

        updated_plan = patch.apply(model_dump(self.app.plan))
        self.app.plan = type(self.app.plan)(**updated_plan)
        return "Application plan updated successfully!"
