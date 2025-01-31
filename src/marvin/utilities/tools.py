import inspect
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, Literal, TypeVar

import pydantic_ai
from pydantic_ai import RunContext

from marvin.utilities.logging import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


def update_fn(
    *,
    name: str | None = None,
    description: str | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Rename a function and optionally set its docstring.

    Can be used as a decorator with keyword arguments only.

    Args:
        name: The new name for the function (optional). If provided, must not be empty.
        description: Optional docstring for the function

    Example:
        # With name:
        @update_fn(name='hello_there')
        def my_fn(x):
            return x

        # With name and description:
        @update_fn(name='hello_there', description='Says hello')
        def my_fn(x):
            return x

        # With no arguments:
        @update_fn()
        def my_fn(x):
            return x

        # Works with async functions too:
        @update_fn(name='async_hello')
        async def my_async_fn(x):
            return x
    """
    if name is not None and not name:
        raise ValueError("name cannot be empty if provided")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                return await func(*args, **kwargs)
        else:

            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                return func(*args, **kwargs)

        if name is not None:
            wrapper.__name__ = name
        if description is not None:
            wrapper.__doc__ = description
        return wrapper

    return decorator


@dataclass
class ResultTool:
    type: Literal["result-tool"] = "result-tool"

    def run(self, ctx: RunContext) -> None:
        pass


def wrap_tool_errors(tool_fn: Callable[..., Any]):
    """
    Pydantic AI doesn't catch errors except for ModelRetry, so we need to make
    sure we catch them ourselves and raise a ModelRetry instead.
    """
    if inspect.iscoroutinefunction(tool_fn):

        @wraps(tool_fn)
        async def _fn(*args, **kwargs):
            try:
                return await tool_fn(*args, **kwargs)
            except pydantic_ai.ModelRetry as e:
                logger.debug(f"Tool failed: {e}")
                raise e
            except Exception as e:
                logger.debug(f"Tool failed: {e}")
                raise pydantic_ai.ModelRetry(message=f"Tool failed: {e}") from e

        return _fn

    else:

        @wraps(tool_fn)
        def _fn(*args: Any, **kwargs: Any):
            try:
                return tool_fn(*args, **kwargs)
            except pydantic_ai.ModelRetry as e:
                logger.debug(f"Tool failed: {e}")
                raise e
            except Exception as e:
                logger.debug(f"Tool failed: {e}")
                raise pydantic_ai.ModelRetry(message=f"Tool failed: {e}") from e

        return _fn
