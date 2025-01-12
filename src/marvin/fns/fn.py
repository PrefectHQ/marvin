import inspect
import json
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import marvin
from marvin.agents.agent import Agent
from marvin.engine.thread import Thread
from marvin.utilities.asyncio import run_sync
from marvin.utilities.logging import get_logger
from marvin.utilities.types import PythonFunction

T = TypeVar("T")
logger = get_logger(__name__)

PROMPT = """
You are an expert at predicting the output of Python functions. You will be given:
1. A function definition with all relevant details, including its docstring, type hints, and parameters
2. The actual values that will be passed to the function
3. You will NOT be given the function's implementation or source code, only its definition

Your job is to predict what this function would return if it were actually executed.
Use the type hints, docstring, and parameter values to make an accurate prediction.
"""


def fn(
    func: Callable[..., T] | None = None,
    *,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
) -> Callable[..., T]:
    """A decorator that predicts the output of a Python function without executing it.

    Can be used with or without parameters:
        @fn
        def my_function(): ...

        @fn(instructions="Be precise")
        def my_function(): ...

    The decorated function accepts additional kwargs:
        - _agent: Override the agent at call time
        - _thread: Override the thread at call time

    Args:
        func: The function to decorate
        instructions: Optional instructions to guide the prediction
        agent: Optional custom agent to use
        thread: Optional thread for maintaining conversation context

    Returns:
        A wrapped function that predicts output instead of executing

    """

    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        is_coroutine_fn = inspect.iscoroutinefunction(f)

        @wraps(f)
        def wrapper(
            *args: Any,
            _agent: Agent | None = None,
            _thread: Thread | str | None = None,
            _instructions: str | None = None,
            **kwargs: Any,
        ) -> T:
            coro = _fn(
                f,
                args,
                kwargs,
                instructions=_instructions or instructions,
                agent=_agent or agent,
                thread=_thread or thread,
            )
            if is_coroutine_fn:
                return coro
            return run_sync(coro)

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


async def _fn(
    func: Callable[..., T],
    fn_args: tuple[Any, ...],
    fn_kwargs: dict[str, Any],
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
) -> T:
    """Predicts the output of a Python function without executing it.

    Args:
        func: The function to predict output for
        fn_args: Positional arguments that would be passed to the function
        fn_kwargs: Keyword arguments that would be passed to the function
        instructions: Optional instructions to guide the prediction
        agent: Optional custom agent to use
        thread: Optional thread for maintaining conversation context

    Returns:
        The predicted output matching the function's return type

    """
    model = PythonFunction.from_function_call(func, *fn_args, **fn_kwargs)

    # Get the return annotation, defaulting to str if not specified
    original_return_annotation = model.return_annotation
    has_return_annotation = original_return_annotation is not inspect.Signature.empty
    model.return_annotation = (
        original_return_annotation if has_return_annotation else str
    )

    model_context = {
        k: v
        for k, v in model.__dict__.items()
        # Don't include bound parameters, function, source code, or return value
        # bound parameters and return value are provided directly as context;
        # the function object isn't interpretable by an LLM; and the source code
        # is misleading because (if it exists) it produces useful context but
        # isn't actually what we're trying to predict
        if k not in {"bound_parameters", "function", "source_code", "return_value"}
    }

    context = {
        "Function definition": model_context,
        "Function arguments": model.bound_parameters,
        "Additional context provided at runtime": model.return_value,
    }
    if instructions:
        context["Additional instructions"] = instructions

    assert model.return_annotation is not None, "No return annotation found"

    task = marvin.Task[T](
        name="Function Output Prediction",
        instructions=PROMPT,
        context=context,
        result_type=model.return_annotation,
        agent=agent,
    )

    result = await task.run_async(thread=thread, handlers=[])

    # If no return annotation was specified, try to parse as JSON first
    if not has_return_annotation:
        try:
            result = json.loads(result)  # type: ignore
        except Exception:
            logger.warning("Failed to parse result as JSON, returning raw result")

    return result
