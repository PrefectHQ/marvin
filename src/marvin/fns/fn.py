import inspect
import json
from collections.abc import Callable
from dataclasses import asdict
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import marvin
from marvin.agents.agent import Agent
from marvin.thread import Thread
from marvin.utilities.asyncio import run_sync
from marvin.utilities.logging import get_logger
from marvin.utilities.types import PythonFunction

T = TypeVar("T", infer_variance=True)
P = ParamSpec("P")
logger = get_logger(__name__)

PROMPT = """
You are an expert at predicting the output of Python functions. You will be given:
1. A function definition with all relevant details, including its docstring, type hints, and parameters
2. The actual values that will be passed to the function
3. Any additional context that was provided at runtime
4. You will NOT be given the function's implementation or source code, only its definition

Your job is to predict what this function would return if it were actually executed.
Use the type hints, docstring, and parameter values to make an accurate prediction.

When returning a string, do not add unecessary quotes.
"""


def _build_task(
    func: Callable[P, T],
    fn_args: tuple[Any, ...],
    fn_kwargs: dict[str, Any],
    instructions: str | None = None,
    agent: Agent | None = None,
) -> marvin.Task[T]:
    """Build a Task for predicting the output of a Python function.

    Args:
        func: The function to predict output for
        fn_args: Positional arguments that would be passed to the function
        fn_kwargs: Keyword arguments that would be passed to the function
        instructions: Optional instructions to guide the prediction
        agent: Optional custom agent to use

    Returns:
        A Task configured to predict the function's output
    """
    context: dict[str, Any] = {}

    model = PythonFunction[P, T].from_function_call(func, *fn_args, **fn_kwargs)

    # Get the return annotation, defaulting to str if not specified
    original_return_annotation = model.return_annotation
    if original_return_annotation is inspect.Signature.empty:
        model.return_annotation = str
        context["JSON result"] = (
            "If possible, your answer will be parsed by json.loads()"
        )

    # exclude bound_parameters, function, source_code, return_value
    model_context = {
        "signature": str(model.signature),
        "name": model.name,
        "parameters": [asdict(p) for p in model.parameters],
        "docstring": model.docstring,
        "return_annotation": model.return_annotation,
    }

    context.update(
        {
            "Function definition": model_context,
            "Function arguments": model.bound_parameters,
            "Additional context": model.return_value,
        }
    )
    if instructions:
        context["Additional instructions"] = instructions

    assert model.return_annotation is not None, "No return annotation found"

    return marvin.Task[T](
        name=f"Predict output of {func.__name__}",
        instructions=PROMPT,
        context=context,
        result_type=model.return_annotation,
        agents=[agent] if agent else None,
    )


def fn(
    func: Callable[P, T] | None = None,
    *,
    instructions: str | None = None,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]] | Callable[P, T]:
    """A decorator that predicts the output of a Python function without executing it.

    Can be used with or without parameters:
        @fn
        def my_function(): ...

        @fn(instructions="Be precise")
        def my_function(): ...

    The decorated function accepts additional kwargs:
        - _agent: Override the agent at call time
        - _thread: Override the thread at call time

    If the function does not have a return annotation, the result will be
    returned as a string and attempted to be parsed as JSON.

    The decorated function also gains an as_task() method that returns the underlying
    marvin Task without executing it.

    Args:
        func: The function to decorate
        instructions: Optional instructions to guide the prediction
        agent: Optional custom agent to use
        thread: Optional thread for maintaining conversation context

    Returns:
        A wrapped function that predicts output instead of executing

    """

    def decorator(f: Callable[P, T]) -> Callable[P, T]:
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
                return coro  # type: ignore[return-value]
            return run_sync(coro)

        def as_task(
            *args: Any,
            _agent: Agent | None = None,
            _instructions: str | None = None,
            **kwargs: Any,
        ) -> marvin.Task[T]:
            """Return a Task configured to predict this function's output."""
            return _build_task(
                f,
                args,
                kwargs,
                instructions=_instructions or instructions,
                agent=_agent or agent,
            )

        wrapper.as_task = as_task  # type: ignore
        return wrapper

    if func is None:
        return decorator
    return decorator(func)


async def _fn(
    func: Callable[P, T],
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
    task = _build_task(func, fn_args, fn_kwargs, instructions=instructions, agent=agent)
    result = await task.run_async(thread=thread, handlers=[])

    if "JSON result" in task.context:
        try:
            result = json.loads(result)  # type: ignore
        except Exception:
            logger.debug("Failed to parse result as JSON, returning raw result")

    return result
