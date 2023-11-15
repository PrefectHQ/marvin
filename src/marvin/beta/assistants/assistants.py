from typing import TYPE_CHECKING, Callable, Optional, Union

from pydantic import BaseModel, Field, field_validator

import marvin.utilities.tools
from marvin.requests import Tool
from marvin.tools.assistants import AssistantTools
from marvin.utilities.asyncio import (
    ExposeSyncMethodsMixin,
    expose_sync_method,
    run_sync,
)
from marvin.utilities.logging import get_logger
from marvin.utilities.openai import get_client

from .threads import Thread

if TYPE_CHECKING:
    from .runs import Run

logger = get_logger("Assistants")


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
    tools: Optional[list[Tool]] = None
    run: OpenAIRun = None
    steps: list[OpenAIRunStep] = []
    messages: list[OpenAIMessage] = []

    @field_validator("tools")
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

        # get any new messages
        new_messages = await self.thread.refresh_messages_async(
            after_message=self.messages[-1].id if self.messages else None
        )
        for m in new_messages:
            if m.created_at >= self.run.created_at and m.role == "assistant":
                self.messages.append(m)

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
                tool = None
                for t in self.assistant.tools if self.tools is None else self.tools:
                    if (
                        t.type == "function"
                        and t.function.name == tool_call.function.name
                    ):
                        tool = t
                        break
                if not tool:
                    output = f"Error: could not find tool {tool_call.function.name}"
                    logger.error(output)
                else:
                    logger.debug(
                        f"Calling {tool.function.name} with args:"
                        f" {tool_call.function.arguments}"
                    )
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        output = tool.function.fn(**arguments)
                        if output is None:
                            output = "<this function produced no output>"
                        if not isinstance(output, str):
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

        while self.run.status in ("queued", "in_progress", "requires_action"):
            await self._process_one_step()
            await self.refresh()
            if self.run.status in ("queued", "in_progress"):
                await asyncio.sleep(0.1)

        if self.run.status == "failed":
            logger.debug(f"Run failed. Last error was: {self.run.last_error}")

        return self
