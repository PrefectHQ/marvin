"""
Asynchronous Utilities
=======================

This module provides utility functions to facilitate asynchronous programming.
It includes methods for creating background tasks, running synchronous functions
asynchronously, and executing coroutines from synchronous contexts.

Key Functions:
--------------
- `create_task`: Safely creates a background task to prevent garbage collection issues.
- `run_async`: Executes a synchronous function asynchronously.
- `run_sync`: Runs a coroutine from a synchronous context, handling various runtimes.

Note:
-----
These utilities are designed to handle special cases such as Jupyter notebooks where
the event loop runs on the main thread and to ensure background tasks are not 
prematurely garbage collected.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, Coroutine, TypeVar

T = TypeVar("T")

BACKGROUND_TASKS: set[asyncio.Task[Any]] = set()


def create_task(coro: Coroutine[Any, Any, T]) -> asyncio.Task[T]:
    """
    Safely creates a background task to prevent it from being garbage collected.

    Args:
    - coro (Coroutine): The coroutine to run as a background task.

    Returns:
    - asyncio.Task: The created task.

    Reference:
    ----------
    https://textual.textualize.io/blog/2023/02/11/the-heisenbug-lurking-in-your-async-code/
    """

    task = asyncio.create_task(coro)
    BACKGROUND_TASKS.add(task)
    task.add_done_callback(BACKGROUND_TASKS.discard)
    return task


async def run_async(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Runs a synchronous function asynchronously.

    Args:
    - func (Callable): The synchronous function to run.
    - *args: Positional arguments to pass to the function.
    - **kwargs: Keyword arguments to pass to the function.

    Returns:
    - T: The result of the function execution.
    """

    loop = asyncio.get_event_loop()

    async def wrapper() -> T:
        try:
            return await loop.run_in_executor(None, partial(func, *args, **kwargs))
        except Exception as e:
            # propagate the exception to the caller
            raise e from None

    return await wrapper()


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """
    Runs a coroutine from a synchronous context.

    If there is no event loop running, the coroutine will be run in a new one.
    If an event loop is running in environments like Jupyter notebooks, a thread
    is spawned to run the event loop.

    Args:
    - coro (Coroutine): The coroutine to run synchronously.

    Returns:
    - T: The result of the coroutine execution.
    """

    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return asyncio.run(coro)
    except RuntimeError:
        return asyncio.run(coro)
