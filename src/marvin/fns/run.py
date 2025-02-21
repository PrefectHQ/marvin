from collections.abc import Callable
from typing import Any, TypeVar

import marvin.utilities.asyncio
from marvin import Task, Thread
from marvin.agents.actor import Actor
from marvin.engine.handlers import AsyncHandler, Handler
from marvin.engine.orchestrator import Orchestrator

T = TypeVar("T")


async def run_tasks_async(
    tasks: list[Task[Any]],
    thread: Thread | str | None = None,
    raise_on_failure: bool = True,
    handlers: list[Handler | AsyncHandler] | None = None,
) -> list[Task[Any]]:
    orchestrator = Orchestrator(
        tasks=tasks,
        thread=thread,
        handlers=handlers,
    )
    await orchestrator.run(raise_on_failure=raise_on_failure)
    return tasks


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
    instructions: str,
    result_type: type[T] = str,
    tools: list[Callable[..., Any]] = [],
    thread: Thread | str | None = None,
    agents: list[Actor] | None = None,
    handlers: list[Handler | AsyncHandler] | None = None,
    raise_on_failure: bool = True,
    **kwargs: Any,
) -> T:
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
    instructions: str,
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
