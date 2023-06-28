import asyncio
import datetime
import math
from enum import Enum
from typing import Any, Union
from zoneinfo import ZoneInfo

from jsonpatch import JsonPatch
from pydantic import BaseModel, Field, PrivateAttr, validator

import marvin
from marvin.engines.language_models import ChatLLM
from marvin.models.history import History, HistoryFilter
from marvin.models.messages import Message, Role
from marvin.prompts import library as prompt_library
from marvin.prompts import render_prompts
from marvin.tools import Tool
from marvin.utilities.types import LoggerMixin

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
    
    # Instructions
    
    Your primary job is to maintain the application's `state` and your own
    `ai_state`. Together, these two states fully parameterize the application,
    making it resilient, serializable, and observable. You do this autonomously;
    you do not need to inform the user of any changes you make. 
    
    # Actions
    
    Each time the user runs the application by sending a message, you must take
    the following steps:
    
    {% if app.ai_state_enabled -%}
    - Call the `UpdateAIState` function to update your own state. Use your state
    to track notes, objectives, in-progress work, and to break problems down
    into solvable, possibly dependent parts. You state consists of a few
    fields:
        - `notes`: a list of notes you have taken. Notes are free-form text and
        can be used to track anything you want to remember, such as
        long-standing user instructions, or observations about how to behave
        or operate the application. These are exclusively related to your role
        as intermediary and you interact with the user and application. Do not
        track application data or state here.
        - `tasks`: a list of tasks you are working on. Tasks track goals,
        milestones, in-progress work, and break problems down into all the
        discrete steps needed to solve them. You should create a new task for
        any work that will require a function call other than updating state,
        or will require more than one state update to complete. You do not
        need to create tasks for simple state updates. Use optional parent
        tasks to indicate nested relationships; parent tasks are not completed
        until all their children are complete. Use optional upstream tasks to
        indicate dependencies; a task can not be completed until its upstream
        tasks are completed.
    {%- endif %}

    - Call any functions necessary to achieve the application's purpose.
    
    - Call the `UpdateAppState` function to update the application's state. This
    is where you should store any information relevant to the application
    itself.

    You can call these functions at any time, in any order, as necessary.
    Finally, respond to the user with an informative message. Remember that the
    user is probably uninterested in the internal steps you took, so respond
    only in a manner appropriate to the application's purpose.
    """
APPLICATION_DETAILS_PROMPT = """
    # Application details
    
    ## Name
    
    {{ app.name }}
    
    ## Description
    
    ```
    {% if app.class_description -%}
    {{ app.class_description }}
    
    {% endif -%}
    {{ app.description }}
    ```
    
    ## Application state
    
    {{ app.state.json() }}
    
    ### Application state schema
    
    {{ app.state.schema_json() }}
    
    {% if app.ai_state_enabled %}
    ## AI (your) state
    
    {{ app.ai_state.json() }}
    
    ### AI state schema
    
    {{ app.ai_state.schema_json() }}
    {% endif %}
    """


class TaskState(Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Task(BaseModel):
    class Config:
        validate_assignment = True

    id: int
    description: str
    upstream_task_ids: list[int] = None
    parent_task_id: int = None
    state: TaskState = TaskState.IN_PROGRESS


class AIState(BaseModel):
    tasks: list[Task] = []
    notes: list[str] = []


class FreeformState(BaseModel):
    state: dict[str, Any] = {}


class AIApplication(LoggerMixin, BaseModel):
    name: str = None
    description: str
    state: BaseModel = Field(default_factory=FreeformState)
    ai_state: AIState = Field(default_factory=AIState)
    tools: list[Tool] = []
    history: History = Field(default_factory=History)
    class_description: str = Field(
        None,
        description=(
            "A description of the application class that can be used for specialized"
            " documentation while still allowing users to overwrite `description`."
        ),
    )
    ai_state_enabled: bool = True

    @validator("tools", pre=True)
    def validate_tools(cls, v):
        v = [t.as_tool() if isinstance(t, AIApplication) else t for t in v]
        return v

    @validator("name", always=True)
    def validate_name(cls, v):
        if v is None:
            v = cls.__name__
        return v

    async def run(self, input_text: str = None, model: ChatLLM = None):
        start_time = datetime.datetime.now(ZoneInfo("UTC"))
        if model is None:
            model = ChatLLM()

        # set up prompts
        prompts = [
            # system prompts
            prompt_library.System(content=SYSTEM_PROMPT),
            prompt_library.System(content=APPLICATION_DETAILS_PROMPT),
            # add current datetime
            prompt_library.Now(),
            # get the history of messages between user and assistant
            prompt_library.MessageHistory(
                history=self.history,
                skip=1,
                filter=HistoryFilter(role_in=[Role.USER, Role.ASSISTANT]),
            ),
            # get the user's latest input with higher priority the history
            prompt_library.User(content="{{ input_text }}"),
            # get the history of function outputs for this specific call
            prompt_library.MessageHistory(
                history=self.history,
                filter=HistoryFilter(role_in=[Role.FUNCTION], timestamp_ge=start_time),
            ),
        ]

        # get latest user input
        input_text = input_text or ""
        self.logger.debug_kv("User input", input_text, key_style="green")
        input_message = Message(role=Role.USER, content=input_text)
        self.history.add_message(input_message)

        # set up tools
        tools = self.tools.copy()
        tools.append(UpdateAppState(app=self))
        if self.ai_state_enabled:
            tools.append(UpdateAIState(app=self))

        i = 1
        max_iterations = marvin.settings.ai_application_max_iterations or math.inf
        while i <= max_iterations:
            messages = render_prompts(
                prompts, render_kwargs=dict(app=self, input_text=input_text)
            )

            response = await model.run(
                messages=messages,
                functions=[t.as_openai_function() for t in tools],
                function_call="auto" if i < max_iterations else "none",
            )

            self.history.add_message(response)
            i += 1

            # if the result was a function call, then run the LLM again
            # TODO: find a good way to support short-circuiting execution
            # e.g. raise a END exception
            if response.role != Role.FUNCTION:
                break

        self.logger.debug_kv("AI response", response.content, key_style="blue")
        return response

    def as_tool(self, name: str = None) -> Tool:
        return AIApplicationTool(app=self, name=name)


class AIApplicationTool(Tool):
    app: "AIApplication"

    def __init__(self, **kwargs):
        if "name" not in kwargs:
            kwargs["name"] = type(self.app).__name__
        super().__init__(**kwargs)

    def run(self, input_text: str) -> str:
        return asyncio.run(self.app.run(input_text))


class JSONPatchModel(BaseModel):
    op: str
    path: str
    value: Union[str, float, int, bool, list, dict] = None
    from_: str = Field(None, alias="from")

    class Config:
        allow_population_by_field_name = True


class UpdateAppState(Tool):
    """
    Updates state using JSON Patch documents.
    """

    _app: "AIApplication" = PrivateAttr()
    description = """
        Update the application state by providing a list of JSON patch
        documents. The state must always comply with the application state's
        JSON schema.
        """

    def __init__(self, app: AIApplication, **kwargs):
        self._app = app
        super().__init__(**kwargs)

    def run(self, patches: list[JSONPatchModel]):
        patch = JsonPatch(patches)
        updated_state = patch.apply(self._app.state.dict())
        self._app.state = type(self._app.state)(**updated_state)
        return "Application state updated successfully!"


class UpdateAIState(Tool):
    """
    Updates state using JSON Patch documents.
    """

    _app: "AIApplication" = PrivateAttr()
    description = """
        Update the AI state by providing a list of JSON patch
        documents. The state must always comply with the AI state's JSON schema.
        """

    def __init__(self, app: AIApplication, **kwargs):
        self._app = app
        super().__init__(**kwargs)

    def run(self, patches: list[JSONPatchModel]):
        patch = JsonPatch(patches)
        updated_state = patch.apply(self._app.ai_state.dict())
        self._app.ai_state = type(self._app.ai_state)(**updated_state)
        return "AI state updated successfully!"
