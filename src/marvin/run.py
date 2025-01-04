from typing import Any, TypeVar

from marvin import Task, Thread
from marvin.agents.actor import Actor
from marvin.engine.orchestrator import Orchestrator
from marvin.utilities.asyncio import run_sync

T = TypeVar("T")


async def run_tasks_async(
    tasks: list[Task[Any]],
    agents: list[Actor] | None = None,
    thread: Thread | str | None = None,
    raise_on_failure: bool = True,
) -> list[Task[Any]]:
    orchestrator = Orchestrator(tasks=tasks, agents=agents, thread=thread)
    await orchestrator.run(raise_on_failure=raise_on_failure)
    return tasks


def run_tasks(
    tasks: list[Task[Any]],
    agents: list[Actor] | None = None,
    thread: Thread | str | None = None,
    raise_on_failure: bool = True,
) -> list[Task[Any]]:
    return run_sync(run_tasks_async(tasks, agents, thread, raise_on_failure))


async def run_async(
    instructions: str,
    result_type: type[T] = str,
    thread: Thread | str | None = None,
    agent: Actor | None = None,
    raise_on_failure: bool = True,
) -> T:
    task = Task[result_type](
        instructions=instructions,
        result_type=result_type,
        agent=agent,
    )
    await run_tasks_async([task], thread=thread, raise_on_failure=raise_on_failure)
    return task.result


def run(
    instructions: str,
    result_type: type[T] = str,
    thread: Thread | str | None = None,
    agent: Actor | None = None,
    raise_on_failure: bool = True,
) -> T:
    return run_sync(
        run_async(
            instructions=instructions,
            result_type=result_type,
            thread=thread,
            agent=agent,
            raise_on_failure=raise_on_failure,
        )
    )
