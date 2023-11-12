import asyncio
from typing import Callable, Optional, Union

from openai.types.beta.threads import ThreadMessage as OpenAIMessage
from openai.types.beta.threads.run import Run as OpenAIRun
from openai.types.beta.threads.runs import RunStep as OpenAIRunStep
from pydantic import BaseModel, Field, field_validator

import marvin.utilities.tools
from marvin.requests import CodeInterpreterTool, FunctionTool, RetrievalTool, Tool
from marvin.utilities.asyncio import (
    ExposeSyncMethodsMixin,
    expose_sync_method,
    run_sync,
)
from marvin.utilities.logging import get_logger
from marvin.utilities.openai import get_client
from marvin.utilities.pydantic import parse_as

logger = get_logger("Assistants")

Retrieval = RetrievalTool()
CodeInterpreter = CodeInterpreterTool()

AssistantTools = list[Union[FunctionTool, RetrievalTool, CodeInterpreterTool, Tool]]


class Thread(BaseModel, ExposeSyncMethodsMixin):
    id: Optional[str] = None
    metadata: dict = {}
    messages: list[OpenAIMessage] = Field([], repr=False)

    def __enter__(self):
        self.create()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete()
        # If an exception has occurred, you might want to handle it or pass it through
        # Returning False here will re-raise any exception that occurred in the context
        return False

    @expose_sync_method("create")
    async def create_async(self, messages: list[str] = None):
        """
        Creates a thread.
        """
        if self.id is not None:
            raise ValueError("Thread has already been created.")
        if messages is not None:
            messages = [{"role": "user", "content": message} for message in messages]
        client = get_client()
        response = await client.beta.threads.create(messages=messages)
        self.id = response.id
        return self

    @expose_sync_method("add")
    async def add_async(
        self, message: str, file_paths: Optional[list[str]] = None
    ) -> OpenAIMessage:
        """
        Add a user message to the thread.
        """
        client = get_client()

        if self.id is None:
            await self.create_async()

        # Upload files and collect their IDs
        file_ids = []
        for file_path in file_paths or []:
            with open(file_path, mode="rb") as file:
                response = await client.files.create(file=file, purpose="assistants")
                file_ids.append(response.id)

        # Create the message with the attached files
        response = await client.beta.threads.messages.create(
            thread_id=self.id, role="user", content=message, file_ids=file_ids
        )
        return OpenAIMessage.model_validate(response.model_dump())

    @expose_sync_method("refresh_messages")
    async def refresh_messages_async(
        self,
        limit: int = None,
        before_message: Optional[str] = None,
        after_message: Optional[str] = None,
    ) -> list[OpenAIMessage]:
        """
        Refresh the messages in the thread.
        """
        if self.id is None:
            await self.create_async()
        client = get_client()

        response = await client.beta.threads.messages.list(
            thread_id=self.id,
            # note that because messages are returned in descending order,
            # we reverse "before" and "after" to the API
            before=after_message,
            after=before_message,
            limit=limit,
        )

        messages = parse_as(list[OpenAIMessage], response.model_dump()["data"])

        if not messages:
            return []

        # update messages with latest data for each ID
        current_messages = {m.id: m for m in self.messages}
        current_messages.update({m.id: m for m in messages})
        self.messages = list(
            sorted(current_messages.values(), key=lambda m: m.created_at)
        )

        # keep up to 2500 messages locally
        self.messages = self.messages[-2500:]

    @expose_sync_method("delete")
    async def delete_async(self):
        client = get_client()
        await client.beta.threads.delete(thread_id=self.id)
        self.id = None

    @expose_sync_method("run")
    async def run_async(
        self,
        assistant: "Assistant",
        **run_kwargs,
    ) -> "Run":
        """
        Creates and returns a `Run` of this thread with the provided assistant.
        """
        if self.id is None:
            await self.create_async()

        return await Run(assistant=assistant, thread=self, **run_kwargs).run_async()


class Assistant(BaseModel, ExposeSyncMethodsMixin):
    id: Optional[str] = None
    name: str = "Assistant"
    model: str = "gpt-4-1106-preview"
    instructions: Optional[str] = Field(None, repr=False)
    tools: AssistantTools = []
    file_ids: list[str] = []
    metadata: dict[str, str] = {}

    default_thread: Thread = Field(
        default_factory=Thread,
        repr=False,
        description="A default thread for the assistant.",
    )

    def clear_default_thread(self):
        self.default_thread = Thread()

    @expose_sync_method("say")
    async def say_async(
        self,
        message: str,
        file_paths: Optional[list[str]] = None,
        message_callback: Optional[Callable] = None,
        run_step_callback: Optional[Callable] = None,
        **run_kwargs,
    ) -> "Run":
        """
        A convenience method for adding a user message to the assistant's
        default thread, running the assistant, and returning the assistant's
        messages.
        """
        if message:
            msg = await self.default_thread.add_async(message, file_paths=file_paths)
            if message_callback:
                message_callback(msg)

        run = await self.default_thread.run_async(
            assistant=self,
            message_callback=message_callback,
            run_step_callback=run_step_callback,
            **run_kwargs,
        )
        return run

    @field_validator("tools", mode="before")
    def format_tools(cls, tools: list[Union[Tool, Callable]]):
        return [
            tool if isinstance(tool, Tool) else FunctionTool.from_function(tool)
            for tool in tools
        ]

    def __enter__(self):
        self.create()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete()
        # If an exception has occurred, you might want to handle it or pass it through
        # Returning False here will re-raise any exception that occurred in the context
        return False

    @expose_sync_method("create")
    async def create_async(self):
        if self.id is not None:
            raise ValueError("Assistant has already been created.")
        client = get_client()
        response = await client.beta.assistants.create(
            **self.model_dump(exclude={"id", "default_thread"}),
        )
        self.id = response.id

    @expose_sync_method("delete")
    async def delete_async(self):
        if self.id:
            client = get_client()
            await client.beta.assistants.delete(assistant_id=self.id)

    @classmethod
    def load(cls, assistant_id: str):
        return run_sync(cls.load_async(assistant_id))

    @classmethod
    async def load_async(cls, assistant_id: str):
        client = get_client()
        response = await client.beta.assistants.retrieve(assistant_id=assistant_id)
        return cls.model_validate(response)


class Run(BaseModel):
    thread: Thread
    assistant: Assistant
    instructions: Optional[str] = Field(
        None, description="Replacement instructions to use for the run."
    )
    additional_instructions: Optional[str] = Field(
        None,
        description=(
            "Additional instructions to append to the assistant's instructions."
        ),
    )
    tools: Optional[AssistantTools] = None
    run: OpenAIRun = None
    steps: list[OpenAIRunStep] = []
    messages: list[OpenAIMessage] = []
    run_step_callback: Optional[Callable] = None
    message_callback: Optional[Callable] = None

    @field_validator("tools", mode="before")
    def format_tools(cls, tools: Union[None, list[Union[Tool, Callable]]]):
        if tools is not None:
            return [
                tool if isinstance(tool, Tool) else FunctionTool.from_function(tool)
                for tool in tools
            ]

    async def refresh(self):
        client = get_client()
        self.run = await client.beta.threads.runs.retrieve(
            run_id=self.run.id, thread_id=self.thread.id
        )

        # refresh the thread's messages
        await self.thread.refresh_messages_async()

        # get any new or updated messages
        current_messages = {m.id: m for m in self.messages}
        for m in self.thread.messages:
            if m.created_at < self.run.created_at or m.role != "assistant":
                continue
            if current_messages.get(m.id) != m:
                # sometimes messages have no content (yet)
                if m.content[0].text.value == "":
                    continue
                if self.message_callback:
                    self.message_callback(m)
                current_messages[m.id] = m
        self.messages = list(
            sorted(current_messages.values(), key=lambda m: m.created_at)
        )

        # get any new or updated steps
        run_steps = await client.beta.threads.runs.steps.list(
            run_id=self.run.id,
            thread_id=self.thread.id,
        )

        current_steps = {step.id: step for step in self.steps}
        for step in reversed(run_steps.data):
            if current_steps.get(step.id) != step:
                if self.run_step_callback:
                    self.run_step_callback(step)
                current_steps[step.id] = step

        self.steps = list(sorted(current_steps.values(), key=lambda s: s.created_at))

    async def _handle_step_requires_action(self):
        client = get_client()
        if self.run.status != "requires_action":
            return
        if self.run.required_action.type == "submit_tool_outputs":
            tool_outputs = []
            for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
                try:
                    output = marvin.utilities.tools.call_function(
                        tools=(
                            self.assistant.tools if self.tools is None else self.tools
                        ),
                        function_name=tool_call.function.name,
                        function_arguments_json=tool_call.function.arguments,
                    )
                except Exception as exc:
                    output = f"Error calling function {tool_call.function.name}: {exc}"
                    logger.error(output)
                tool_outputs.append(
                    dict(tool_call_id=tool_call.id, output=output or "")
                )

            await client.beta.threads.runs.submit_tool_outputs(
                thread_id=self.thread.id, run_id=self.run.id, tool_outputs=tool_outputs
            )

    async def run_async(self) -> "Run":
        client = get_client()

        create_kwargs = {}
        if self.instructions is not None:
            create_kwargs["instructions"] = self.instructions
        if self.additional_instructions is not None:
            create_kwargs["instructions"] = (
                create_kwargs.get("instructions", self.assistant.instructions)
                + "\n\n"
                + self.additional_instructions
            )
        if self.tools is not None:
            create_kwargs["tools"] = self.tools
        self.run = await client.beta.threads.runs.create(
            thread_id=self.thread.id, assistant_id=self.assistant.id, **create_kwargs
        )

        while self.run.status in ("queued", "in_progress", "requires_action"):
            if self.run.status == "requires_action":
                await self._handle_step_requires_action()
            await asyncio.sleep(0.1)
            await self.refresh()

        if self.run.status == "failed":
            logger.debug(f"Run failed. Last error was: {self.run.last_error}")

        return self
