from typing import TYPE_CHECKING, Optional

from openai.types.beta.threads import Message
from pydantic import BaseModel, Field

import marvin.utilities.openai
from marvin.utilities.asyncio import (
    ExposeSyncMethodsMixin,
    expose_sync_method,
    run_sync,
)
from marvin.utilities.logging import get_logger

logger = get_logger("Threads")

if TYPE_CHECKING:
    from .assistants import Assistant
    from .runs import Run


class Thread(BaseModel, ExposeSyncMethodsMixin):
    """
    The Thread class represents a conversation thread with an assistant.

    Attributes:
        id (Optional[str]): The unique identifier of the thread. None if the thread
                            hasn't been created yet.
        metadata (dict): Additional data about the thread.
    """

    id: Optional[str] = None
    metadata: dict = {}
    messages: list[Message] = Field([], repr=False)

    def __enter__(self):
        return run_sync(self.__aenter__)

    def __exit__(self, exc_type, exc_val, exc_tb):
        return run_sync(self.__aexit__, exc_type, exc_val, exc_tb)

    async def __aenter__(self):
        await self.create_async()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.delete_async()
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
        client = marvin.utilities.openai.get_openai_client()
        response = await client.beta.threads.create(messages=messages)
        self.id = response.id
        return self

    @expose_sync_method("add")
    async def add_async(
        self,
        message: str,
        role: str = "user",
        code_interpreter_files: Optional[list[str]] = None,
        file_search_files: Optional[list[str]] = None,
        image_files: Optional[list[str]] = None,
    ) -> Message:
        """
        Add a user message to the thread.
        """
        client = marvin.utilities.openai.get_openai_client()

        if self.id is None:
            await self.create_async()

        content = [dict(text=message, type="text")]

        # Upload files and collect their IDs
        attachments = []
        for fp in code_interpreter_files or []:
            with open(fp, mode="rb") as file:
                response = await client.files.create(file=file, purpose="assistants")
                attachments.append(
                    dict(file_id=response.id, tools=[dict(type="code_interpreter")])
                )
        for fp in file_search_files or []:
            with open(fp, mode="rb") as file:
                response = await client.files.create(file=file, purpose="assistants")
                attachments.append(
                    dict(file_id=response.id, tools=[dict(type="file_search")])
                )
        for fp in image_files or []:
            with open(fp, mode="rb") as file:
                response = await client.files.create(file=file, purpose="vision")
                content.append(
                    dict(image_file=dict(file_id=response.id), type="image_file")
                )

        # Create the message with the attached files
        response = await client.beta.threads.messages.create(
            thread_id=self.id, role=role, content=content, attachments=attachments
        )
        return response

    @expose_sync_method("get_messages")
    async def get_messages_async(
        self,
        limit: int = None,
        before_message: Optional[str] = None,
        after_message: Optional[str] = None,
    ) -> list[Message]:
        """
        Asynchronously retrieves messages from the thread.

        Args:
            limit (int, optional): The maximum number of messages to return.
            before_message (str, optional): The ID of the message to start the
                list from, retrieving messages sent before this one.
            after_message (str, optional): The ID of the message to start the
                list from, retrieving messages sent after this one.
        Returns:
            list[Union[Message, dict]]: A list of messages from the thread
        """

        if self.id is None:
            await self.create_async()
        client = marvin.utilities.openai.get_openai_client()

        response = await client.beta.threads.messages.list(
            thread_id=self.id,
            # note that because messages are returned in descending order,
            # we reverse "before" and "after" to the API
            before=after_message,
            after=before_message,
            limit=limit,
            # order desc to get the most recent messages first
            order="desc",
        )
        return list(reversed(response.data))

    @expose_sync_method("delete")
    async def delete_async(self):
        client = marvin.utilities.openai.get_openai_client()
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

        Args:
            assistant (Assistant): The assistant to run the thread with.
            run_kwargs: Additional keyword arguments to pass to the Run constructor.
        """
        if self.id is None:
            await self.create_async()

        from marvin.beta.assistants.runs import Run

        run = Run(
            assistant=assistant,
            thread=self,
            **run_kwargs,
        )
        return await run.run_async()
