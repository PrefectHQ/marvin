from collections.abc import Coroutine
from typing import Any, TypeVar

from unsync import unsync

T = TypeVar("T")


def run_sync(coroutine: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine synchronously.

    This is a wrapper around unsync.unsync that allows you to run a coroutine
    synchronously.

    Example:
    ```python
    async def f(x: int) -> int:
        return x + 1

    result = run_sync(f(1))
    ```

    """

    @unsync
    async def _wrapper(coroutine: Coroutine[Any, Any, T]) -> T:
        return await coroutine

    unfuture = _wrapper(coroutine)
    return unfuture.result()
