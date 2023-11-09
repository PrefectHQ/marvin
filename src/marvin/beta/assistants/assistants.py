import asyncio
import inspect
import json
import uuid
from contextlib import contextmanager
from typing import Any, Optional

from pydantic import BaseModel, validator

from marvin.beta.assistants.types import Message, Run, Tool
from marvin.utilities.asyncutils import (
    ExposeSyncMethodsMixin,
    expose_sync_method,
    run_sync,
)
from marvin.utilities.openai import get_client
from marvin.utilities.pydantic import parse_as


class Thread(BaseModel, ExposeSyncMethodsMixin):
    id: Optional[str] = None
    metadata: dict = {}

    class Config:
        orm_mode = True

    async def _lazy_create(self):
        if self.id is None:
            client = get_client()
            response = await client.beta.threads.create()
            self.id = response.id

    @expose_sync_method("add")
    async def add_async(self, message: str) -> Message:
        """
        Add a user message to the thread.
        """
        client = get_client()

        await self._lazy_create()
        response = await client.beta.threads.messages.create(
            thread_id=self.id, role="user", content=message
        )
        return Message.model_validate(response.model_dump())

    @expose_sync_method("get_messages")
    async def get_messages_async(
        self,
        limit: int = None,
        before_message: Optional[str] = None,
        after_message: Optional[str] = None,
    ) -> list[dict]:
        await self._lazy_create()
        client = get_client()
        response = await client.beta.threads.messages.list(
            thread_id=self.id,
            # note that because messages are returned in descending order,
            # we reverse "before" and "after" to the API
            before=after_message,
            after=before_message,
            limit=limit,
        )
        messages = parse_as(list[Message], response.model_dump()["data"])
        # return messages in ascending order
        return list(reversed(messages))

    @expose_sync_method("delete")
    async def delete_async(self):
        client = get_client()
        await client.beta.threads.delete(thread_id=self.id)

    @expose_sync_method("run")
    async def run_async(self, assistant: "Assistant") -> Run:
        await self._lazy_create()
        return await assistant.run_thread_async(thread=self)


class Assistant(BaseModel, ExposeSyncMethodsMixin):
    id: Optional[str] = None
    name: str
    model: str = "gpt-4-1106-preview"
    instructions: Optional[str] = None
    tools: list[Tool] = []
    file_ids: list[str] = []
    metadata: dict[str, str] = {}

    class Config:
        orm_mode = True

    @validator("tools", pre=True)
    def convert_functions_to_tools(cls, v):
        tools = []
        for tool in v:
            if inspect.isfunction(tool):
                tool = Tool.from_function(tool)
            tools.append(tool)
        return tools

    @classmethod
    def create(cls, **kwargs):
        return run_sync(cls.create_async(**kwargs))

    @classmethod
    async def create_async(cls, **kwargs):
        client = get_client()
        # apply defaults
        obj = cls(**kwargs)
        response = await client.beta.assistants.create(**obj.model_dump(exclude={"id"}))
        response = response.model_dump()
        response["tools"] = kwargs.get("tools", response.get("tools"))
        return cls.model_validate(response)

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
    async def run_thread_async(self, thread: Thread) -> Run:
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
                    tool_outputs = await self._get_tool_outputs(
                        required_action=run.required_action
                    )
                    await client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
                    )

                else:
                    raise ValueError("Invalid required action type")
        return Run.model_validate(run.model_dump())

    async def _get_tool_outputs(self, required_action: dict) -> Any:
        if required_action.type != "submit_tool_outputs":
            raise ValueError("Invalid required action type")

        tool_outputs = []
        for tool_call in required_action.submit_tool_outputs.tool_calls:
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


@contextmanager
def temporary_thread():
    thread = Thread.create()
    try:
        yield thread
    finally:
        thread.delete()


@contextmanager
def TemporaryAssistant(**kwargs):
    if "name" not in kwargs:
        kwargs["name"] = f"Temporary Assistant {uuid.uuid4().hex[:8]}"
    assistant = Assistant.create(**kwargs)
    try:
        yield assistant
    finally:
        assistant.delete()
