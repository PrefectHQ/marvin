import asyncio
import json
from typing import Any, Callable, Optional, Union

from pydantic import BaseModel, field_validator

from marvin.beta.assistants.types import OpenAIMessage, OpenAIRun, RunResponse, Tool
from marvin.utilities.asyncio import (
    ExposeSyncMethodsMixin,
    expose_sync_method,
    run_sync,
)
from marvin.utilities.openai import get_client
from marvin.utilities.pydantic import parse_as


class Thread(BaseModel, ExposeSyncMethodsMixin):
    id: Optional[str] = None
    metadata: dict = {}
    messages: list[OpenAIMessage] = []

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
    ) -> list[dict]:
        """
        Refresh the messages in the thread.

        """
        if limit is None:
            limit = 20
        if after_message is None and self.messages:
            after_message = self.messages[-1].id

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

        # combine messages with existing messages
        # in ascending order
        all_messages = self.messages + list(reversed(messages))

        # ensure messages are unique
        all_messages = {m.id: m for m in all_messages}.values()

        # keep the last 100 messages locally
        self.messages = list(all_messages)[-100:]

    @expose_sync_method("delete")
    async def delete_async(self):
        client = get_client()
        await client.beta.threads.delete(thread_id=self.id)
        self.id = None

    @expose_sync_method("run")
    async def run_async(self, assistant: "Assistant") -> RunResponse:
        if self.id is None:
            await self.create_async()

        return await assistant.run_thread_async(thread=self)


class Assistant(BaseModel, ExposeSyncMethodsMixin):
    id: Optional[str] = None
    name: str
    model: str = "gpt-4-1106-preview"
    instructions: Optional[str] = None
    tools: list[Union[Tool, Callable]] = []
    file_ids: list[str] = []
    metadata: dict[str, str] = {}

    @field_validator("tools")
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

    @expose_sync_method("run_thread")
    async def run_thread_async(self, thread: Thread) -> RunResponse:
        client = get_client()
        run = await client.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=self.id
        )

        while run.status in ("queued", "in_progress", "requires_action"):
            await asyncio.sleep(0.1)
            run = await client.beta.threads.runs.retrieve(
                run_id=run.id, thread_id=thread.id
            )
            if run.status == "requires_action":
                if run.required_action.type == "submit_tool_outputs":
                    tool_outputs = await self._get_tool_outputs(run=run)
                    await client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
                    )

                else:
                    raise ValueError("Invalid required action type")

        # reload thread messages
        await thread.refresh_messages_async()
        # get any messages created after the run's created time
        messages = [
            m
            for m in thread.messages
            if m.created_at >= run.created_at and m.role == "assistant"
        ]
        run_steps = await client.beta.threads.runs.steps.list(
            run_id=run.id, thread_id=thread.id
        )
        return RunResponse(
            run=run, run_steps=reversed(run_steps.data), messages=messages
        )

    async def _get_tool_outputs(self, run: OpenAIRun) -> Any:
        if run.required_action.type != "submit_tool_outputs":
            raise ValueError("Invalid required action type")

        tool_outputs = []
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            if tool_call.type != "function":
                continue
            tool = next(
                (
                    t
                    for t in self.tools
                    if t.type == "function"
                    and t.function.name == tool_call.function.name
                ),
                None,
            )
            if not tool:
                output = f"Error: could not find tool {tool_call.function.name}"
            else:
                arguments = json.loads(tool_call.function.arguments)
                try:
                    output = tool.function.fn(**arguments)
                except Exception as exc:
                    print(f"Error: {exc}")
                    output = f"Error calling function {tool.function.name}: {exc}"
            tool_outputs.append(dict(tool_call_id=tool_call.id, output=output))
        return tool_outputs

    # def as_tool(self, delegate=True) -> Tool:
    #     def run_assistant(thread_id: str = None):
