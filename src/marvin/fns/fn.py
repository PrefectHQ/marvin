from dataclasses import asdict
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import marvin
from marvin.agents.agent import Agent
from marvin.engine.thread import Thread
from marvin.utilities.types import PythonFunction

T = TypeVar("T")

PROMPT = """
You are an expert at predicting the output of Python functions. You will be given:
1. A function definition with all relevant details, including its docstring, type hints, and parameters
2. The actual values that will be passed to the function
3. You will NOT be given the function's implementation or source code, only its definition

Your job is to predict what this function would return if it were actually executed.
Use the type hints, docstring, and parameter values to make an accurate prediction.
"""


def fn(
    func: Optional[Callable[..., T]] = None,
    *,
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> Callable[..., T]:
    """
    A decorator that predicts the output of a Python function without executing it.

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
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Extract marvin-specific kwargs
            _agent = kwargs.pop("_agent", None)
            _thread = kwargs.pop("_thread", None)

            return _fn(
                f,
                args,
                kwargs,
                instructions=instructions,
                agent=_agent or agent,
                thread=_thread or thread,
            )

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


def _fn(
    func: Callable[..., T],
    fn_args: tuple[Any, ...],
    fn_kwargs: dict[str, Any],
    instructions: Optional[str] = None,
    agent: Optional[Agent] = None,
    thread: Optional[Thread | str] = None,
) -> T:
    """
    Predicts the output of a Python function without executing it.

    Args:
        func: The function to predict output for
        *args: Positional arguments that would be passed to the function
        instructions: Optional instructions to guide the prediction
        agent: Optional custom agent to use
        thread: Optional thread for maintaining conversation context
        **kwargs: Keyword arguments that would be passed to the function

    Returns:
        The predicted output matching the function's return type
    """
    model = PythonFunction.from_function_call(func, *fn_args, **fn_kwargs)

    model_context = {
        k: v
        for k, v in asdict(model).items()
        if k not in {"bound_parameters", "function"}
    }

    context = {
        "Function definition": model_context,
        "Function arguments": model.bound_parameters,
    }
    if instructions:
        context["Additional instructions"] = instructions

    task = marvin.Task(
        name="Function Output Prediction",
        instructions=PROMPT,
        context=context,
        result_type=model.return_annotation,
        agent=agent,
    )

    return task.run(thread=thread)
