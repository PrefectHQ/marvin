from typing import Optional, TypeVar

from marvin import Agent, Task, Thread
from marvin.engine.orchestrator import Orchestrator
from marvin.utilities.asyncio import run_sync

T = TypeVar("T")


async def run_async(
    instructions: str,
    result_type: type[T] = str,
    thread: Optional[Thread | str] = None,
    agent: Optional[Agent | str] = None,
    raise_on_failure: bool = True,
) -> T:
    task = Task(instructions=instructions, result_type=result_type, agent=agent)
    await run_tasks_async([task], thread=thread, raise_on_failure=raise_on_failure)
    return task.result


async def run_tasks_async(
    tasks: list[Task],
    thread: Optional[Thread | str] = None,
    raise_on_failure: bool = True,
) -> list[Task]:
    orchestrator = Orchestrator(tasks=tasks, thread=thread)
    await orchestrator.run(raise_on_failure=raise_on_failure)
    return tasks


def run(
    instructions: str,
    result_type: type[T] = str,
    thread: Optional[Thread | str] = None,
    agent: Optional[Agent | str] = None,
    raise_on_failure: bool = True,
) -> T:
    return run_sync(
        run_async(instructions, result_type, thread, agent, raise_on_failure)
    )
