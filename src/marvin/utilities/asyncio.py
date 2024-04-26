"""Utilities for working with asyncio."""

import asyncio
import functools
import inspect
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from typing import Any, Callable, Coroutine, TypeVar, cast

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


async def run_async(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Runs a synchronous function in an asynchronous manner.

    Args:
        fn: The function to run.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The return value of the function.

    Example:
        Basic usage:
        ```python
        def my_sync_function(x: int) -> int:
            return x + 1

        await run_async(my_sync_function, 1)
        ```
    """

    async def wrapper() -> T:
        try:
            return await loop.run_in_executor(
                None, functools.partial(fn, *args, **kwargs)
            )
        except Exception as e:
            # propagate the exception to the caller
            raise e

    loop = asyncio.get_event_loop()
    return await wrapper()


def run_sync(coroutine: Coroutine[Any, Any, T]) -> T:
    """
    Runs a coroutine from a synchronous context. A thread will be spawned
    to run the event loop if necessary, which allows coroutines to run in
    environments like Jupyter notebooks where the event loop runs on the main
    thread.

    Args:
        coroutine: The coroutine to run.

    Returns:
        The return value of the coroutine.

    Example:
        Basic usage:
        ```python
        async def my_async_function(x: int) -> int:
            return x + 1

        run_sync(my_async_function(1))
        ```
    """
    # ensure context variables are properly copied to the async frame
    context = copy_context()
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with ThreadPoolExecutor() as executor:
            future = executor.submit(context.run, asyncio.run, coroutine)
            return future.result()
    else:
        return context.run(asyncio.run, coroutine)


def run_sync_if_awaitable(obj: Any) -> Any:
    """
    If the object is awaitable, run it synchronously. Otherwise, return the
    object.

    Args:
        obj: The object to run.

    Returns:
        The return value of the object if it is awaitable, otherwise the object
        itself.

    Example:
        Basic usage:
        ```python
        async def my_async_function(x: int) -> int:
            return x + 1

        run_sync_if_awaitable(my_async_function(1))
        ```
    """
    return run_sync(obj) if inspect.isawaitable(obj) else obj


def make_sync(async_func):
    """
    Creates a synchronous function from an asynchronous function.
    """

    @functools.wraps(async_func)
    def sync_func(*args, **kwargs):
        return run_sync(async_func(*args, **kwargs))

    sync_func.__signature__ = inspect.signature(async_func)
    sync_func.__doc__ = async_func.__doc__
    return sync_func


class ExposeSyncMethodsMixin:
    """
    A mixin that can take functions decorated with `expose_sync_method`
    and automatically create synchronous versions.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for method in list(cls.__dict__.values()):
            if callable(method) and hasattr(method, "_sync_name"):
                sync_method_name = method._sync_name
                setattr(cls, sync_method_name, method._sync_wrapper)


def expose_sync_method(name: str) -> Callable[..., Any]:
    """
    Decorator that automatically exposes synchronous versions of async methods.
    Note it doesn't work with classmethods.

    Args:
        name: The name of the synchronous method.

    Returns:
        The decorated function.

    Example:
        Basic usage:
        ```python
        class MyClass(ExposeSyncMethodsMixin):

            @expose_sync_method("my_method")
            async def my_method_async(self):
                return 42

        my_instance = MyClass()
        await my_instance.my_method_async() # returns 42
        my_instance.my_method()  # returns 42
        ```
    """

    def decorator(
        async_method: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(async_method)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            coro = async_method(*args, **kwargs)
            return run_sync(coro)

        # Cast the sync_wrapper to the same type as the async_method to give the
        # type checker the needed information.
        casted_sync_wrapper = cast(Callable[..., T], sync_wrapper)

        # Attach attributes to the async wrapper
        setattr(async_method, "_sync_wrapper", casted_sync_wrapper)
        setattr(async_method, "_sync_name", name)

        # return the original async method; the sync wrapper will be added to
        # the class by the init hook
        return async_method

    return decorator
