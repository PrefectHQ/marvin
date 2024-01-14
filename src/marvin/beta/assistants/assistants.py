from typing import TYPE_CHECKING, Callable, Optional, Union

from pydantic import BaseModel, Field

import marvin.utilities.tools
from marvin.tools.assistants import AssistantTool
from marvin.types import Tool
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
    tools: list[Union[AssistantTool, Callable]] = []
    file_ids: list[str] = []
    metadata: dict[str, str] = {}

    default_thread: Thread = Field(
        default_factory=Thread,
        repr=False,
        description="A default thread for the assistant.",
    )

    def clear_default_thread(self):
        self.default_thread = Thread()

    def get_tools(self) -> list[AssistantTool]:
        return [
            (
                tool
                if isinstance(tool, Tool)
                else marvin.utilities.tools.tool_from_function(tool)
            )
            for tool in self.tools
        ]

    def get_instructions(self) -> str:
        return self.instructions or ""

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

    def __enter__(self):
        self.create()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete()
        # If an exception has occurred, you might want to handle it or pass it through
        # Returning False here will re-raise any exception that occurred in the context
        return False

    async def __aenter__(self):
        breakpoint()
        await self.create_async()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.delete_async()
        # If an exception has occurred, you might want to handle it or pass it through
        # Returning False here will re-raise any exception that occurred in the context
        return False

    @expose_sync_method("create")
    async def create_async(self):
        if self.id is not None:
            raise ValueError("Assistant has already been created.")
        client = get_client()
        response = await client.beta.assistants.create(
            **self.model_dump(
                include={"name", "model", "metadata", "file_ids", "metadata"}
            ),
            tools=[tool.model_dump() for tool in self.get_tools()],
            instructions=self.get_instructions(),
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

    def chat(self, thread: Thread = None):
        if thread is None:
            thread = self.default_thread
        return thread.chat(assistant=self)

    def pre_run_hook(self, run: "Run"):
        pass

    def post_run_hook(self, run: "Run"):
        pass
