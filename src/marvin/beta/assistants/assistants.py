import asyncio
import json
from typing import Callable, Optional, Union

from openai.types.beta.threads import ThreadMessage as OpenAIMessage
from openai.types.beta.threads.run import Run as OpenAIRun
from openai.types.beta.threads.runs import RunStep as OpenAIRunStep
from pydantic import BaseModel, Field, field_validator

from marvin.beta.assistants.types import Tool
from marvin.utilities.asyncio import (
    ExposeSyncMethodsMixin,
    expose_sync_method,
    run_sync,
)
from marvin.utilities.logging import get_logger
from marvin.utilities.openai import get_client
from marvin.utilities.pydantic import parse_as

logger = get_logger("Assistant")


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
    async def add_async(self, message: str) -> OpenAIMessage:
        """
        Add a user message to the thread.
        """
        client = get_client()

        if self.id is None:
            await self.create_async()
        response = await client.beta.threads.messages.create(
            thread_id=self.id, role="user", content=message
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

        new_message_ids = {m.id for m in messages}

        all_messages = sorted(
            [m for m in self.messages if m.id not in new_message_ids] + messages,
            key=lambda m: m.created_at,
        )

        # keep up to 2500 messages locally
        self.messages = list(all_messages)[-2500:]

    @expose_sync_method("delete")
    async def delete_async(self):
        client = get_client()
        await client.beta.threads.delete(thread_id=self.id)
        self.id = None

    @expose_sync_method("run")
    async def run_async(
        self,
        assistant: "Assistant",
        instructions: str = None,
        additional_instructions: str = None,
    ) -> "Run":
        """
        Creates and returns a `Run` of this thread with the provided assistant.

        Arguments:
            assistant: The assistant to run.
            instructions: Replacement instructions to use for the assistant.
            additional_instructions: Additional instructions to append to the
            assistant's instructions.
        """
        if self.id is None:
            await self.create_async()

        return await Run(
            assistant=assistant,
            thread=self,
            instructions=instructions,
            additional_instructions=additional_instructions,
        ).run_async()

    @expose_sync_method("say")
    async def say_async(
        self,
        message: str,
        assistant: "Assistant",
        instructions: str = None,
        additional_instructions: str = None,
    ) -> list[OpenAIMessage]:
        """
        A convenience method for adding a user message, running an assistant,
        and returning the assistant's messages.

        Arguments:
            message: The message to send to the assistant.
            assistant: The assistant to run.
            instructions: Replacement instructions to use for the assistant.
            additional_instructions: Additional instructions to append to the
                assistant's instructions.
        """
        if message:
            await self.add_async(message)
        run = await self.run_async(
            assistant=assistant,
            instructions=instructions,
            additional_instructions=additional_instructions,
        )
        return run.messages


class Assistant(BaseModel, ExposeSyncMethodsMixin):
    id: Optional[str] = None
    name: str
    model: str = "gpt-4-1106-preview"
    instructions: Optional[str] = Field(None, repr=False)
    tools: list[Tool] = []
    file_ids: list[str] = []
    metadata: dict[str, str] = {}

    @field_validator("tools", mode="before")
    def format_tools(cls, tools: list[Union[Tool, Callable]]):
        return [
            tool if isinstance(tool, Tool) else Tool.from_function(tool)
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
            **self.model_dump(exclude={"id"}),
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
    tools: Optional[list[Tool]] = None
    run: OpenAIRun = None
    steps: list[OpenAIRunStep] = []
    messages: list[OpenAIMessage] = []

    @field_validator("tools", mode="before")
    def format_tools(cls, tools: Union[None, list[Union[Tool, Callable]]]):
        if tools is not None:
            return [
                tool if isinstance(tool, Tool) else Tool.from_function(tool)
                for tool in tools
            ]

    async def _process_one_step(self):
        if self.run.status == "requires_action":
            await self._process_step_requires_action()
        await self.refresh()

    async def refresh(self):
        client = get_client()
        self.run = await client.beta.threads.runs.retrieve(
            run_id=self.run.id, thread_id=self.thread.id
        )

        # refresh the thread's messages
        await self.thread.refresh_messages_async()

        self.messages = [
            m
            for m in self.thread.messages
            if m.created_at >= self.run.created_at and m.role == "assistant"
        ]

        # get any new steps
        run_steps = await client.beta.threads.runs.steps.list(
            run_id=self.run.id,
            thread_id=self.thread.id,
            # the default order is descending, so we use `before` to get steps
            # that are chronologically `after`
            before=self.steps[-1].id if self.steps else None,
        )
        self.steps.extend(reversed(run_steps.data))

    async def _process_step_requires_action(self):
        client = get_client()
        if self.run.status != "requires_action":
            return
        if self.run.required_action.type == "submit_tool_outputs":
            tool_outputs = []
            for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
                if tool_call.type != "function":
                    continue
                tool = next(
                    (
                        t
                        for t in self.assistant.tools
                        if t.type == "function"
                        and t.function.name == tool_call.function.name
                    ),
                    None,
                )
                if not tool:
                    output = f"Error: could not find tool {tool_call.function.name}"
                else:
                    logger.debug(
                        f"Calling {tool.function.name} with args:"
                        f" {tool_call.function.arguments}"
                    )
                    arguments = json.loads(tool_call.function.arguments)
                    try:
                        output = tool.function.fn(**arguments)
                        if output is None:
                            output = "<this function produced no output>"
                        output = json.dumps(output)
                        logger.debug(f"{tool.function.name} output: {output}")
                    except Exception as exc:
                        output = f"Error calling function {tool.function.name}: {exc}"
                        logger.error(f"{tool.function.name} output: {output}")
                tool_outputs.append(dict(tool_call_id=tool_call.id, output=output))

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

        first_step = True

        while self.run.status in ("queued", "in_progress", "requires_action"):
            if not first_step:
                await asyncio.sleep(0.1)
                first_step = False
            await self._process_one_step()
            await self.refresh()

        if self.run.status == "failed":
            logger.debug(f"Run failed. Last error was: {self.run.last_error}")

        return self
