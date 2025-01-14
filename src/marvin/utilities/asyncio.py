import asyncio
import contextvars
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine synchronously.

    This function uses asyncio to run a coroutine in a synchronous context.
    It will create or get an event loop and run the coroutine to completion.
    Context variables are properly propagated between threads.

    Example:
    ```python
    async def f(x: int) -> int:
        return x + 1

    result = run_sync(f(1))
    ```

    Args:
        coro: The coroutine to run synchronously

    Returns:
        The result of the coroutine
    """
    ctx = contextvars.copy_context()
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return ctx.run(asyncio.run, coro)
    else:
        try:
            return ctx.run(loop.run_until_complete, coro)
        except RuntimeError as e:
            return run_sync_in_thread(coro)
            raise RuntimeError(
                "Marvin's sync API can not be called from an async frame. Please use the async API instead."
            ) from e


def run_sync_in_thread(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine synchronously in a new thread.

    This function creates a new thread with its own event loop to run the coroutine.
    Context variables are properly propagated between threads.
    This is useful when you need to run async code in a context where you can't use
    the current event loop (e.g., inside an async frame).

    Example:
    ```python
    async def f(x: int) -> int:
        return x + 1

    result = run_sync_in_thread(f(1))
    ```

    Args:
        coro: The coroutine to run synchronously

    Returns:
        The result of the coroutine
    """
    result: T | None = None
    error: BaseException | None = None
    done = threading.Event()
    ctx = contextvars.copy_context()

    def thread_target() -> None:
        nonlocal result, error
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = ctx.run(loop.run_until_complete, coro)
        except BaseException as e:
            error = e
        finally:
            loop.close()
            asyncio.set_event_loop(None)
            done.set()

    thread = threading.Thread(target=thread_target)
    thread.start()
    done.wait()

    if error is not None:
        raise error

    return result
