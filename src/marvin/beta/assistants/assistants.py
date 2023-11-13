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

    async def get_messages_async(
        self,
        limit: int = None,
        before_message: Optional[str] = None,
        after_message: Optional[str] = None,
    ):
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
            order="desc",
        )

        return parse_as(list[OpenAIMessage], reversed(response.model_dump()["data"]))

    async def refresh_messages_async(self):
        """
        Asynchronously refreshes and updates the message list.

        This function fetches the latest messages up to a specified limit and
        checks if the latest message in the current message list
        (`self.messages`) is included in the new batch. If the latest message is
        missing, it continues to fetch additional messages in batches, up to a
        maximum count, using pagination. The function then updates
        `self.messages` with these new messages, ensuring any existing messages
        are updated with their latest versions and new messages are appended in
        their original order.
        """
        # fetch up to 100 messages
        max_fetched = 100
        limit = 50
        max_attempts = max_fetched / limit + 2

        # Fetch the latest messages
        messages = await self.get_messages_async(limit=limit)

        if not messages:
            return

        # Check if the latest message in self.messages is in the new messages
        latest_message_id = self.messages[-1].id if self.messages else None
        missing_latest = (
            latest_message_id not in {m.id for m in messages}
            if latest_message_id
            else True
        )

        # If the latest message is missing, fetch additional messages
        total_fetched = len(messages)
        attempts = 0
        while (
            messages
            and missing_latest
            and total_fetched < max_fetched
            and attempts < max_attempts
        ):
            attempts += 1
            paginated_messages = await self.get_messages_async(
                limit=limit, before_message=messages[0].id
            )
            total_fetched += len(paginated_messages)
            # prepend messages
            messages = paginated_messages + messages
            if any(m.id == latest_message_id for m in paginated_messages):
                missing_latest = False

        # Update self.messages with the latest data
        new_messages_dict = {m.id: m for m in messages}
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i].id in new_messages_dict:
                self.messages[i] = new_messages_dict.pop(self.messages[i].id)
            else:
                break
        # Append remaining new messages at the end in their original order
        self.messages.extend(new_messages_dict.values())

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
        **run_kwargs,
    ) -> "Run":
        """
        A convenience method for adding a user message to the assistant's
        default thread, running the assistant, and returning the assistant's
        messages.
        """
        if message:
            await self.default_thread.add_async(message, file_paths=file_paths)

        run = await self.default_thread.run_async(
            assistant=self,
            **run_kwargs,
        )
        return run

    @field_validator("tools", mode="before")
    def format_tools(cls, tools: list[Union[Tool, Callable]]):
        return [
            (
                tool
                if isinstance(tool, Tool)
                else marvin.utilities.tools.tool_from_function(tool)
            )
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
        self.clear_default_thread()

    @expose_sync_method("delete")
    async def delete_async(self):
        if not self.id:
            raise ValueError("Assistant has not been created.")
        client = get_client()
        await client.beta.assistants.delete(assistant_id=self.id)
        self.id = None

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

    @field_validator("tools", mode="before")
    def format_tools(cls, tools: Union[None, list[Union[Tool, Callable]]]):
        if tools is not None:
            return [
                (
                    tool
                    if isinstance(tool, Tool)
                    else marvin.utilities.tools.tool_from_function(tool)
                )
                for tool in tools
            ]

    async def refresh(self):
        client = get_client()
        self.run = await client.beta.threads.runs.retrieve(
            run_id=self.run.id, thread_id=self.thread.id
        )

        # refresh the thread's messages
        await self.thread.refresh_messages_async()
        self.messages = [m for m in self.thread.messages if m.run_id == self.run.id]

        await self.refresh_run_steps_async()

    async def refresh_run_steps_async(self):
        """
        Asynchronously refreshes and updates the run steps list.

        This function fetches the latest run steps up to a specified limit and
        checks if the latest run step in the current run steps list
        (`self.steps`) is included in the new batch. If the latest run step is
        missing, it continues to fetch additional run steps in batches, up to a
        maximum count, using pagination. The function then updates
        `self.steps` with these new run steps, ensuring any existing run steps
        are updated with their latest versions and new run steps are appended in
        their original order.
        """
        # fetch up to 100 run steps
        max_fetched = 100
        limit = 50
        max_attempts = max_fetched / limit + 2

        # Fetch the latest run steps
        client = get_client()

        response = await client.beta.threads.runs.steps.list(
            run_id=self.run.id,
            thread_id=self.thread.id,
            limit=limit,
        )
        run_steps = list(reversed(response.data))

        if not run_steps:
            return

        # Check if the latest run step in self.steps is in the new run steps
        latest_step_id = self.steps[-1].id if self.steps else None
        missing_latest = (
            latest_step_id not in {rs.id for rs in run_steps}
            if latest_step_id
            else True
        )

        # If the latest run step is missing, fetch additional run steps
        total_fetched = len(run_steps)
        attempts = 0
        while (
            run_steps
            and missing_latest
            and total_fetched < max_fetched
            and attempts < max_attempts
        ):
            attempts += 1
            response = await client.beta.threads.runs.steps.list(
                run_id=self.run.id,
                thread_id=self.thread.id,
                limit=limit,
                # because this is a raw API call, "after" refers to pagination
                # in descnding chronological order
                after=run_steps[0].id,
            )
            paginated_steps = list(reversed(response.data))

            total_fetched += len(paginated_steps)
            # prepend run steps
            run_steps = paginated_steps + run_steps
            if any(rs.id == latest_step_id for rs in paginated_steps):
                missing_latest = False

        # Update self.steps with the latest data
        new_steps_dict = {rs.id: rs for rs in run_steps}
        for i in range(len(self.steps) - 1, -1, -1):
            if self.steps[i].id in new_steps_dict:
                self.steps[i] = new_steps_dict.pop(self.steps[i].id)
            else:
                break
        # Append remaining new run steps at the end in their original order
        self.steps.extend(new_steps_dict.values())

    async def _handle_step_requires_action(self):
        client = get_client()
        if self.run.status != "requires_action":
            return
        if self.run.required_action.type == "submit_tool_outputs":
            tool_outputs = []
            for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
                try:
                    output = marvin.utilities.tools.call_function_tool(
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
