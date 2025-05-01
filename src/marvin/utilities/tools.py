import inspect
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, Literal, ParamSpec, TypeVar

import pydantic_ai
from pydantic_ai import RunContext

from marvin.utilities.logging import get_logger

T = TypeVar("T")
P = ParamSpec("P")
logger = get_logger(__name__)


def update_fn(
    func: Callable[..., T] | None = None,
    /,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]] | Callable[P, T]:
    """Update a function's name and optionally set its docstring.

    Can be used either as a decorator with keyword arguments or as a direct function.

    Args:
        func: The function to update (optional). If provided, updates are applied directly.
             If not provided, returns a decorator.
        name: The new name for the function (optional). If provided, must not be empty.
        description: Optional docstring for the function

    Example:
        # As a function:
        def my_fn(x):
            return x
        updated_fn = update_fn(my_fn, name='hello_there')

        # As a decorator with name:
        @update_fn(name='hello_there')
        def my_fn(x):
            return x

        # As a decorator with name and description:
        @update_fn(name='hello_there', description='Says hello')
        def my_fn(x):
            return x

        # As a decorator with no arguments:
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

    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                return await fn(*args, **kwargs)
        else:

            @wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                return fn(*args, **kwargs)

        if name is not None:
            wrapper.__name__ = name
        if description is not None:
            wrapper.__doc__ = description
        return wrapper

    # If func is provided, apply the decorator directly
    if func is not None:
        return decorator(func)

    # Otherwise return the decorator for use with @ syntax
    return decorator


@dataclass
class ResultTool:
    type: Literal["result-tool"] = "result-tool"

    def run(self, ctx: RunContext) -> None:
        pass


def wrap_tool_errors(tool_fn: Callable[P, T]):
    """
    Pydantic AI doesn't catch errors except for ModelRetry, so we need to make
    sure we catch them ourselves and raise a ModelRetry instead.
    """
    if inspect.iscoroutinefunction(tool_fn):

        @wraps(tool_fn)
        async def _fn(*args: P.args, **kwargs: P.kwargs):
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
        def _fn(*args: P.args, **kwargs: P.kwargs):
            try:
                return tool_fn(*args, **kwargs)
            except pydantic_ai.ModelRetry as e:
                logger.debug(f"Tool failed: {e}")
                raise e
            except Exception as e:
                logger.debug(f"Tool failed: {e}")
                raise pydantic_ai.ModelRetry(message=f"Tool failed: {e}") from e

        return _fn
