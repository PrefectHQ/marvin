"""Module for NLI tool utilities."""

import inspect
import json
from functools import update_wrapper
from typing import Any, Callable, Optional

import pydantic

from marvin.requests import Function, Tool
from marvin.utilities.asyncio import run_sync
from marvin.utilities.logging import get_logger

logger = get_logger("Tools")


def custom_partial(func: Callable, **fixed_kwargs: Any) -> Callable:
    """
    Returns a new function with partial application of the given keyword arguments.
    The new function has the same __name__ and docstring as the original, and its
    signature excludes the provided kwargs.
    """

    # Define the new function with a dynamic signature
    def wrapper(**kwargs):
        # Merge the provided kwargs with the fixed ones, prioritizing the former
        all_kwargs = {**fixed_kwargs, **kwargs}
        return func(**all_kwargs)

    # Update the wrapper function's metadata to match the original function
    update_wrapper(wrapper, func)

    # Modify the signature to exclude the fixed kwargs
    original_sig = inspect.signature(func)
    new_params = [
        param
        for param in original_sig.parameters.values()
        if param.name not in fixed_kwargs
    ]
    wrapper.__signature__ = original_sig.replace(parameters=new_params)

    return wrapper


def tool_from_function(
    fn: Callable[..., Any],
    name: Optional[str] = None,
    description: Optional[str] = None,
    kwargs: Optional[dict[str, Any]] = None,
):
    """
    Creates an OpenAI-CLI tool from a Python function.

    If any kwargs are provided, they will be stored and provided at runtime.
    Provided kwargs will be removed from the tool's parameter schema.
    """
    if kwargs:
        fn = custom_partial(fn, **kwargs)

    schema = pydantic.TypeAdapter(
        fn, config=pydantic.ConfigDict(arbitrary_types_allowed=True)
    ).json_schema()

    return Tool(
        type="function",
        function=Function.create(
            name=name or fn.__name__,
            description=description or fn.__doc__,
            parameters=schema,
            _python_fn=fn,
        ),
    )


def call_function_tool(
    tools: list[Tool], function_name: str, function_arguments_json: str
):
    tool = next(
        (
            tool
            for tool in tools
            if isinstance(tool, Tool)  # type: ignore
            and tool.function
            and tool.function.name == function_name
        ),
        None,
    )
    if (
        not tool
        or not tool.function
        or not tool.function._python_fn
        or not tool.function.name
    ):
        raise ValueError(f"Could not find function '{function_name}'")

    arguments = json.loads(function_arguments_json)
    logger.debug_kv(
        f"{tool.function.name}", f"called with arguments: {arguments}", "green"
    )
    output = tool.function._python_fn(**arguments)
    if inspect.isawaitable(output):
        output = run_sync(output)
    truncated_output = str(output)[:100]
    if len(truncated_output) < len(str(output)):
        truncated_output += "..."
    logger.debug_kv(f"{tool.function.name}", f"returned: {truncated_output}", "green")
    if not isinstance(output, str):
        output = json.dumps(output)
    return output
