import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, TypeVar

T = TypeVar("T")

BACKGROUND_TASKS = set()


def create_task(coro):
    """
    Creates async background tasks in a way that is safe from garbage
    collection.

    See
    https://textual.textualize.io/blog/2023/02/11/the-heisenbug-lurking-in-your-async-code/

    Example:

    async def my_coro(x: int) -> int:
        return x + 1

    # safely submits my_coro for background execution
    create_task(my_coro(1))
    """  # noqa: E501
    task = asyncio.create_task(coro)
    BACKGROUND_TASKS.add(task)
    task.add_done_callback(BACKGROUND_TASKS.discard)
    return task


async def run_async(func, *args, **kwargs) -> T:
    """
    Runs a synchronous function in an asynchronous manner.
    """

    async def wrapper() -> T:
        try:
            return await loop.run_in_executor(
                None, functools.partial(func, *args, **kwargs)
            )
        except Exception as e:
            # propagate the exception to the caller
            raise e

    loop = asyncio.get_event_loop()
    return await wrapper()


def run_sync(coroutine: Awaitable[T]) -> T:
    """
    Runs a coroutine from a synchronous context, either in the current event
    loop or in a new one if there is no event loop running. The coroutine will
    block until it is done. A thread will be spawned to run the event loop if
    necessary, which allows coroutines to run in environments like Jupyter
    notebooks where the event loop runs on the main thread.

    """
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coroutine)
                return future.result()
        else:
            return asyncio.run(coroutine)
    except RuntimeError:
        return asyncio.run(coroutine)
