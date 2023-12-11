import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Coroutine, TypeVar, cast

T = TypeVar("T")


async def run_async(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Runs a synchronous function in an asynchronous manner.

    Args:
        fn: The function to run.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The return value of the function.
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


class ExposeSyncMethodsMixin:
    """
    A mixin class that can take functions decorated with `expose_sync_method` and
    automatically create synchronous versions.


    Example:

    class MyClass(ExposeSyncMethodsMixin):

        @expose_sync_method("my_method")
        async def my_method_async(self):
            return 42

    my_instance = MyClass()
    await my_instance.my_method_async() # returns 42
    my_instance.my_method()  # returns 42
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

    Example:

    class MyClass(ExposeSyncMethodsMixin):

        @expose_sync_method("my_method")
        async def my_method_async(self):
            return 42

    my_instance = MyClass()
    await my_instance.my_method_async() # returns 42
    my_instance.my_method()  # returns 42
    """

    def decorator(
        async_method: Callable[..., Coroutine[Any, Any, T]]
    ) -> Callable[..., T]:
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
