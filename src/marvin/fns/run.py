import asyncio
from collections.abc import Callable, Sequence
from typing import Annotated, Any, AsyncGenerator, TypeVar

from pydantic_ai.messages import UserContent

import marvin
import marvin.utilities.asyncio
from marvin import Task, Thread
from marvin.agents.actor import Actor
from marvin.engine.events import Event
from marvin.engine.orchestrator import Orchestrator
from marvin.handlers.handlers import AsyncHandler, Handler

T = TypeVar("T")


async def run_tasks_async(
    tasks: list[Task[Any]],
    thread: Thread | str | None = None,
    raise_on_failure: bool = True,
    handlers: list[Handler | AsyncHandler] | None = None,
) -> list[Task[Any]] | AsyncGenerator[Event, None]:
    orchestrator = Orchestrator(
        tasks=tasks,
        thread=thread,
        handlers=handlers,
    )
    await orchestrator.run(raise_on_failure=raise_on_failure)
    return tasks


async def run_tasks_stream(
    tasks: list[Task[Any]],
    thread: Thread | str | None = None,
    raise_on_failure: bool = True,
    handlers: list[Handler | AsyncHandler] | None = None,
) -> AsyncGenerator[Event, None]:
    # Create and configure the queue handler.
    queue_handler = marvin.handlers.QueueHandler()
    handlers = (handlers or []) + [queue_handler]

    # Initialize the orchestrator with the handlers.
    orchestrator = Orchestrator(
        tasks=tasks,
        thread=thread,
        handlers=handlers,
    )

    # Start the orchestrator in the background.
    orchestrator_task = asyncio.create_task(
        orchestrator.run(raise_on_failure=raise_on_failure)
    )

    try:
        # Continue looping until the orchestrator finishes.
        while not orchestrator_task.done():
            try:
                # Wait for the next event from the queue.
                event = await asyncio.wait_for(queue_handler.queue.get(), timeout=0.1)
                yield event
            except asyncio.TimeoutError:
                # No event was available in the queue; loop again.
                continue

        # Once the orchestrator has finished, yield any remaining events.
        while not queue_handler.queue.empty():
            yield queue_handler.queue.get_nowait()

    finally:
        # Optionally, cancel the orchestrator if needed.
        if not orchestrator_task.done():
            orchestrator_task.cancel()


def run_tasks(
    tasks: list[Task[Any]],
    thread: Thread | str | None = None,
    raise_on_failure: bool = True,
    handlers: list[Handler | AsyncHandler] | None = None,
) -> list[Task[Any]]:
    return marvin.utilities.asyncio.run_sync(
        run_tasks_async(
            tasks=tasks,
            thread=thread,
            raise_on_failure=raise_on_failure,
            handlers=handlers,
        ),
    )


async def run_async(
    instructions: str | Sequence[UserContent],
    result_type: type[T] | Annotated[T, Any] = str,
    tools: list[Callable[..., Any]] = [],
    thread: Thread | str | None = None,
    agents: list[Actor] | None = None,
    handlers: list[Handler | AsyncHandler] | None = None,
    raise_on_failure: bool = True,
    **kwargs: Any,
) -> T | AsyncGenerator[Event, None]:
    task = Task[result_type](
        instructions=instructions,
        result_type=result_type,
        agents=agents,
        tools=tools,
        **kwargs,
    )
    await run_tasks_async(
        [task],
        thread=thread,
        raise_on_failure=raise_on_failure,
        handlers=handlers,
    )

    return task.result


def run(
    instructions: str | Sequence[UserContent],
    result_type: type[T] = str,
    tools: list[Callable[..., Any]] = [],
    thread: Thread | str | None = None,
    agents: list[Actor] | None = None,
    raise_on_failure: bool = True,
    handlers: list[Handler | AsyncHandler] | None = None,
    **kwargs: Any,
) -> T:
    return marvin.utilities.asyncio.run_sync(
        run_async(
            instructions=instructions,
            result_type=result_type,
            tools=tools,
            thread=thread,
            agents=agents,
            raise_on_failure=raise_on_failure,
            handlers=handlers,
            **kwargs,
        ),
    )


def run_stream(
    instructions: str | Sequence[UserContent],
    result_type: type[T] = str,
    tools: list[Callable[..., Any]] = [],
    thread: Thread | str | None = None,
    agents: list[Actor] | None = None,
    raise_on_failure: bool = True,
    handlers: list[Handler | AsyncHandler] | None = None,
    **kwargs: Any,
) -> AsyncGenerator[Event, None]:
    task = Task[result_type](
        instructions=instructions,
        result_type=result_type,
        agents=agents,
        tools=tools,
        **kwargs,
    )
    return run_tasks_stream(
        [task],
        thread=thread,
        raise_on_failure=raise_on_failure,
        handlers=handlers,
    )
