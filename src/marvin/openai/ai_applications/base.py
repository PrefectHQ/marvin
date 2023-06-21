import inspect
from enum import Enum
from typing import Any, Union

import uvicorn
from fastapi import Body, FastAPI
from jsonpatch import JsonPatch
from langchain.schema import AIMessage
from pydantic import BaseModel, Field, PrivateAttr

from marvin.bot.history import History, InMemoryHistory
from marvin.models.threads import BaseMessage, Message
from marvin.openai.tools.base import Tool
from marvin.utilities.llms import get_model
from marvin.utilities.openai import call_llm_with_tools
from marvin.utilities.strings import jinja_env
from marvin.utilities.types import LoggerMixin, MarvinBaseModel


class ApplicationResponse(BaseMessage):
    parsed_content: Any = None


AI_APP_SYSTEM_MESSAGE = jinja_env.from_string(inspect.cleandoc("""
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
    
    Your primary job is to maintain the application's `state` and `tasks`. You
    do this autonomously; you do not need to inform the user of any changes you
    make. Whenever you receive input from the user, you must perform the
    following steps:
    
    - call the `CreateApplicationTask` or `UpdateApplicationTask` functions to
      create or update the application tasks. Tasks track goals, milestones,
      in-progress work, and break problems down into all the discrete steps
      needed to solve them. You should create a new task for any action you need
      to take beyond directly updating the application's state. By looking at an
      application's tasks, it should be easy to understand what the application
      is doing and what it needs to do next. Parent tasks are optional and
      indicate nested relationships: parent tasks are not completed until all
      their children are complete. Upstream tasks are optional and indicate
      dependencies: a task can not be completed until its upstream tasks are
      completed.
    
    - call any other functions necessary to achieve the application's purpose.
      Each function call should correspond to an in-progress task; use that to
      help you create tasks and track progress.
      
    - call the `UpdateApplicationState` function to update the application's
      `state`. The application is fully parameterized by its state and its
      tasks.
      
    - update application tasks again, if necessary
        
    Finally, respond to the user with an informative message but do not explain
    the internal steps you took above.

    This is the description of the application:
     
    {{ app.description }}
    
    This is the application's current state:
     
    {{ app.state.json() }}
    
    These are the application's current tasks:
     
    [{% for t in app.tasks -%} {{ t.json() }} {%- endfor %}]
    
    Today's date is {{ dt() }}
    
    """))


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


class FreeformState(BaseModel):
    state: dict[str, Any] = {}


class AIApplication(MarvinBaseModel, LoggerMixin):
    description: str
    state: BaseModel = Field(default_factory=FreeformState)
    tasks: list[Task] = []
    tools: list[Tool] = []
    history: History = Field(default_factory=InMemoryHistory)

    async def run(self, input_text: str = None):
        messages = []

        system_message = Message(
            role="system", content=AI_APP_SYSTEM_MESSAGE.render(app=self)
        )
        messages.append(system_message)

        def message_processor(messages: list[Message]) -> list[Message]:
            # update the system message in case the state has changed
            messages[0] = Message(
                role="system", content=AI_APP_SYSTEM_MESSAGE.render(app=self)
            )
            return messages

        historical_messages = await self.history.get_messages()
        messages.extend(historical_messages)

        if input_text:
            self.logger.debug_kv("User input", input_text, key_style="green")
            input_message = Message(role="user", content=input_text)
            await self.history.add_message(input_message)
            messages.append(input_message)

        llm = get_model()
        output = await call_llm_with_tools(
            llm,
            messages=messages,
            tools=self.tools
            + [
                UpdateApplicationState(app=self),
                CreateApplicationTask(app=self),
                UpdateApplicationTask(app=self),
            ],
            message_processor=message_processor,
        )

        if isinstance(output, AIMessage):
            response = ApplicationResponse(role="ai", content=output.content)
        else:
            response = ApplicationResponse(
                role="ai", content=str(output), parsed_content=output
            )

        self.logger.debug_kv("AI response", response.content, key_style="blue")
        await self.history.add_message(response)
        return response

    async def serve(self, host="127.0.0.1", port=8000):
        app = FastAPI()

        state_type = type(self.state)

        @app.get("/state")
        def get_state() -> state_type:
            return self.state

        @app.post("/run")
        async def run(text: str = Body(embed=True)) -> ApplicationResponse:
            return await self.run(text)

        config = uvicorn.config.Config(app=app, host=host, port=port)
        server = uvicorn.Server(config=config)
        await server.serve()


class JSONPatchModel(BaseModel):
    op: str
    path: str
    value: Union[str, float, int, bool, list, dict] = None
    from_: str = Field(None, alias="from")

    class Config:
        allow_population_by_field_name = True


class UpdateApplicationState(Tool):
    """
    Updates state using JSON Patch documents.
    """

    _app: "AIApplication" = PrivateAttr()
    description = """
        Update the application state by providing a list of JSON patch
        documents. The state must always comply with this JSON schema: {{
        TOOL._app.state.schema() }}
        """

    def __init__(self, app: AIApplication, **kwargs):
        self._app = app
        super().__init__(**kwargs)

    def run(self, patches: list[JSONPatchModel]):
        patch = JsonPatch(patches)
        updated_state = patch.apply(self._app.state.dict())
        self._app.state = type(self._app.state)(**updated_state)
        return f"State updated successfully! (payload was {patches})"


class CreateApplicationTask(Tool):
    _app: "AIApplication" = PrivateAttr()
    description = """
        Create a new application task.
        """

    def __init__(self, app: AIApplication, **kwargs):
        self._app = app
        super().__init__(**kwargs)

    def run(self, task: Task):
        self._app.tasks.append(Task(**task))
        return f"Task {task} created successfully!"


class UpdateApplicationTask(Tool):
    _app: "AIApplication" = PrivateAttr()
    description = """
        Update the state of an application task.
        """

    def __init__(self, app: AIApplication, **kwargs):
        self._app = app
        super().__init__(**kwargs)

    def run(self, task_id: int, state: TaskState):
        task = next((t for t in self._app.tasks if t.id == task_id), None)
        if task is None:
            raise ValueError(f"Task with id {task_id} not found!")
        task.state = state
        return f"Task {task_id} updated to {state} successfully!"


# class UpdateApplicationTasks(Tool):
#     """
#     Updates tasks using JSON Patch documents.
#     """

#     _app: "AIApplication" = PrivateAttr()
#     description = f"""
#         Update the application's tasks by providing a list of JSON patch
#         documents. Each task has the following schema: { Task.schema() }.
#         """

#     def __init__(self, app: AIApplication, **kwargs):
#         self._app = app
#         super().__init__(**kwargs)

#     def run(self, patches: list[JSONPatchModel]):
#         patch = JsonPatch(patches)
#         updated_tasks = patch.apply([t.dict() for t in self._app.tasks])
#         self._app.tasks = parse_obj_as(list[Task], updated_tasks)
#         return "Tasks updated successfully!"
