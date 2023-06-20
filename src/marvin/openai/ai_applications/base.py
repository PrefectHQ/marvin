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

    You are the intelligent, natural language interface to an application. The
    application has a structured `state` but no formal API; you are the only way
    to interact with it. You must interpret the user's inputs as attempts to
    interact with the application's state in the context of the application's
    purpose. For example, if the application is a to-do tracker, then "I need to
    go to the store" should be interpreted as an attempt to add a new to-do
    item. If it is a route planner, then "I need to go to the store" should be
    interpreted as an attempt to find a route to the store. 
    
    You may respond to the user and use any other tools to help you interpret
    the user's inputs. However, you are solely responsible for updating the
    application's state. State could represents notes, a game world, statistics
    about ongoing process, or anythine else. In order to update state, you must
    use the `UpdateApplicationState` tool. It will respond with "State updated
    successfully!" If you do not see that message, then state has not been
    updated.
    
    The application is defined as an iterated control loop. After each
    iteration, you can respond to the user and wait for their next input, or you
    can invoke the application yourself and iterate autonomously. This is useful
    for behaviors or tasks that do require user supervision but may require
    multiple introspection cycles. For example, an application for editing
    software might iterate autonomously multiple times to adjust code before
    yielding control back to the user. In order to repeat automatically, call
    the `RepeatApplication()` function with a message. The message will be
    provided to the next iteration of the application as an input. Note that you
    must call this function last, so update state before calling it.
    
    This is the description of the application:
     
    {{ app.description }}
    
    This is the application's current state:
     
    {{ app.state }}
    
    This is the application's state schema, in OpenAPI format:
    
    {{ app.state.schema() }}
    
    Today's date is {{ dt() }}
    
    """))


class TaskState(Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Task(BaseModel):
    id: int
    description: str
    parent_task_id: int = None
    status: TaskState = TaskState.IN_PROGRESS


class FreeformState(BaseModel):
    state: dict[str, Any] = {}


class AIApplication(MarvinBaseModel, LoggerMixin):
    description: str
    state: BaseModel = Field(default_factory=FreeformState)
    tasks: list[Task] = Field(
        default_factory=list, description="Internal tracking of application goals"
    )
    tools: list[Tool] = []
    history: History = Field(default_factory=InMemoryHistory)

    async def run(self, input_text: str = None):
        system_message = Message(
            role="system", content=AI_APP_SYSTEM_MESSAGE.render(app=self)
        )

        def message_processor(messages: list[Message]) -> list[Message]:
            # update the system message in case the state has changed
            messages[0] = Message(
                role="system", content=AI_APP_SYSTEM_MESSAGE.render(app=self)
            )
            return messages

        historical_messages = await self.history.get_messages()

        if input_text:
            self.logger.debug_kv("User input", input_text, key_style="green")
            input_message = Message(role="user", content=input_text)
            await self.history.add_message(input_message)

        llm = get_model()
        output = await call_llm_with_tools(
            llm,
            messages=[system_message, *historical_messages, input_message],
            tools=self.tools
            + [
                UpdateApplicationState(app=self),
                RepeatApplication(),
            ],
            message_processor=message_processor,
        )

        if isinstance(output, RepeatApplicationResponse):
            response = ApplicationResponse(
                role="ai",
                content=(
                    "Automatically invoking the application again with input"
                    f' "{output.message}"'
                ),
            )
            self.logger.debug_kv("AI response", response.content, key_style="blue")
            await self.history.add_message(response)
            await self.run(input_text=output.message)
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

        @app.post("/interact")
        async def interact(text: str = Body(embed=True)) -> ApplicationResponse:
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
    Updates state using JSON Patch documents. Slightly more complex than
    UpdateState, but more effecient for large state objects.
    """

    _app: "AIApplication" = PrivateAttr()
    description = """
        Update the application state by providing a list of JSON Patch
        documents. The state must always comply with this OpenAPI schema: {{
        TOOL._app.state.schema() }}
        """

    def __init__(self, app: AIApplication, **kwargs):
        self._app = app
        super().__init__(**kwargs)

    def run(self, patches: list[JSONPatchModel]):
        patch = JsonPatch(patches)
        updated_state = patch.apply(self._app.state.dict())
        self._app.state = type(self._app.state)(**updated_state)
        return "State updated successfully!"


class RepeatApplicationResponse(BaseModel):
    message: str


class RepeatApplication(Tool):
    description: str = (
        "Call this function with a message to autonomously invoke the application using"
        " the provided message as input. You will not be able to see the function call"
        " history in the new invocation, so write any updates to states before calling"
        " this function."
    )
    is_final: bool = True

    def run(self, message: str) -> RepeatApplicationResponse:
        return RepeatApplicationResponse(message=message)
