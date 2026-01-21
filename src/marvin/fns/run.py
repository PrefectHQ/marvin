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


def _tasks_are_independent(tasks: list[Task[Any]]) -> bool:
    """Check if tasks have no dependencies between each other."""
    for i, task1 in enumerate(tasks):
        for j, task2 in enumerate(tasks):
            if i != j:
                # Check if task1 depends on task2 or vice versa
                if task2 in task1.depends_on or task1 in task2.depends_on:
                    return False
                # Check if they share subtasks or parent relationships
                if task1.parent == task2 or task2.parent == task1:
                    return False
                if task1 in task2.subtasks or task2 in task1.subtasks:
                    return False
    return True


async def run_tasks_async(
    tasks: list[Task[Any]],
    thread: Thread | str | None = None,
    raise_on_failure: bool = True,
    handlers: list[Handler | AsyncHandler] | None = None,
) -> list[Task[Any]] | AsyncGenerator[Event, None]:
    """Run tasks either concurrently (if independent) or sequentially via orchestrator."""
    # If we have multiple independent tasks, run them concurrently
    if len(tasks) > 1 and _tasks_are_independent(tasks):
        # Run independent tasks concurrently using asyncio.gather
        await asyncio.gather(
            *[
                task.run_async(
                    thread=thread, raise_on_failure=raise_on_failure, handlers=handlers
                )
                for task in tasks
            ]
        )
        return tasks
    else:
        # Use orchestrator for dependent tasks or single tasks
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
    """Run tasks either concurrently (if independent) or sequentially."""
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
