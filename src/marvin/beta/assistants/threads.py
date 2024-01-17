import asyncio
import time
from typing import TYPE_CHECKING, Callable, Optional, Union

from openai.types.beta.threads import ThreadMessage
from pydantic import BaseModel, Field, PrivateAttr

from marvin.beta.assistants.formatting import pprint_message
from marvin.utilities.asyncio import (
    ExposeSyncMethodsMixin,
    expose_sync_method,
    run_sync,
)
from marvin.utilities.logging import get_logger
from marvin.utilities.openai import get_openai_client
from marvin.utilities.pydantic import parse_as

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
    messages: list[ThreadMessage] = Field([], repr=False)

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
        client = get_openai_client()
        response = await client.beta.threads.create(messages=messages)
        self.id = response.id
        return self

    @expose_sync_method("add")
    async def add_async(
        self, message: str, file_paths: Optional[list[str]] = None, role: str = "user"
    ) -> ThreadMessage:
        """
        Add a user message to the thread.
        """
        client = get_openai_client()

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
            thread_id=self.id, role=role, content=message, file_ids=file_ids
        )
        return ThreadMessage.model_validate(response.model_dump())

    @expose_sync_method("get_messages")
    async def get_messages_async(
        self,
        limit: int = None,
        before_message: Optional[str] = None,
        after_message: Optional[str] = None,
        json_compatible: bool = False,
    ) -> list[Union[ThreadMessage, dict]]:
        """
        Asynchronously retrieves messages from the thread.

        Args:
            limit (int, optional): The maximum number of messages to return.
            before_message (str, optional): The ID of the message to start the list from,
                                             retrieving messages sent before this one.
            after_message (str, optional): The ID of the message to start the list from,
                                            retrieving messages sent after this one.
            json_compatible (bool, optional): If True, returns messages as dictionaries.
                                              If False, returns messages as ThreadMessage
                                              objects. Default is False.

        Returns:
            list[Union[ThreadMessage, dict]]: A list of messages from the thread, either
                                              as dictionaries or ThreadMessage objects,
                                              depending on the value of json_compatible.
        """

        if self.id is None:
            await self.create_async()
        client = get_openai_client()

        response = await client.beta.threads.messages.list(
            thread_id=self.id,
            # note that because messages are returned in descending order,
            # we reverse "before" and "after" to the API
            before=after_message,
            after=before_message,
            limit=limit,
            order="desc",
        )

        T = dict if json_compatible else ThreadMessage

        return parse_as(list[T], reversed(response.model_dump()["data"]))

    @expose_sync_method("delete")
    async def delete_async(self):
        client = get_openai_client()
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

        run = Run(assistant=assistant, thread=self, **run_kwargs)
        return await run.run_async()

    def chat(self, assistant: "Assistant"):
        """
        Starts an interactive chat session with the provided assistant.
        """

        from marvin.beta.chat_ui import interactive_chat

        if self.id is None:
            self.create()

        def callback(thread_id: str, message: str):
            thread = Thread(id=thread_id)
            thread.run(assistant=assistant)

        with interactive_chat(thread_id=self.id, message_callback=callback):
            while True:
                try:
                    time.sleep(0.2)
                except KeyboardInterrupt:
                    break


class ThreadMonitor(BaseModel, ExposeSyncMethodsMixin):
    """
    The ThreadMonitor class represents a monitor for a specific thread.

    Attributes:
        thread_id (str): The unique identifier of the thread being monitored.
        last_message_id (Optional[str]): The ID of the last message received in the thread.
        on_new_message (Callable): A callback function that is called when a new message
                                   is received in the thread.
    """

    thread_id: str
    last_message_id: Optional[str] = None
    on_new_message: Callable = Field(default=pprint_message)
    _thread: Thread = PrivateAttr()

    @property
    def thread(self):
        return self._thread

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._thread = Thread(id=kwargs["thread_id"])

    @expose_sync_method("run_once")
    async def run_once_async(self):
        messages = await self.get_latest_messages()
        for msg in messages:
            if self.on_new_message:
                self.on_new_message(msg)

    @expose_sync_method("run")
    async def run_async(self, interval_seconds: int = None):
        """
        Run the thread monitor in a loop, checking for new messages every `interval_seconds`.

        Args:
            interval_seconds (int, optional): The number of seconds to wait between
                                              checking for new messages. Default is 1.
        """
        if interval_seconds is None:
            interval_seconds = 1
        if interval_seconds < 1:
            raise ValueError("Interval must be at least 1 second.")

        while True:
            try:
                await self.run_once_async()
            except KeyboardInterrupt:
                logger.debug("Keyboard interrupt received; exiting thread monitor.")
                break
            except Exception as exc:
                logger.error(f"Error refreshing thread: {exc}")
            await asyncio.sleep(interval_seconds)

    async def get_latest_messages(self) -> list[ThreadMessage]:
        limit = 20

        # Loop to get all new messages in batches of 20
        while True:
            messages = await self.thread.get_messages_async(
                after_message=self.last_message_id, limit=limit
            )

            # often the API will retrieve messages that have been created but
            # not populated with text. We filter out these empty messages.
            filtered_messages = []
            for i, msg in enumerate(messages):
                skip_message = False
                for c in msg.content:
                    if getattr(getattr(c, "text", None), "value", None) == "":
                        skip_message = True
                if not skip_message:
                    filtered_messages.append(msg)

            if filtered_messages:
                self.last_message_id = filtered_messages[-1].id

            if len(messages) < limit:
                break

        return filtered_messages
