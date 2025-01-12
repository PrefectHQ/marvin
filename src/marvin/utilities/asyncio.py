import asyncio
import contextvars
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
        return ctx.run(loop.run_until_complete, coro)
