"""Module for NLI tool utilities."""

import inspect
import json
from typing import Any, Callable, Optional

from pydantic import BaseModel

from marvin.requests import Function, Tool
from marvin.utilities.asyncio import run_sync
from marvin.utilities.logging import get_logger
from marvin.utilities.pydantic import cast_callable_to_model

logger = get_logger("Tools")


def tool_from_function(
    fn: Callable[..., Any],
    name: Optional[str] = None,
    description: Optional[str] = None,
):
    model = cast_callable_to_model(fn)
    serializer: Callable[..., dict[str, Any]] = getattr(
        model, "model_json_schema", getattr(model, "schema")
    )

    return Tool[BaseModel](
        type="function",
        function=Function(
            name=name or fn.__name__,
            description=description or fn.__doc__,
            parameters=serializer(),
            python_fn=fn,
        ),
    )


def call_function_tool(
    tools: list[Tool[BaseModel]], function_name: str, function_arguments_json: str
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
        or not tool.function.python_fn
        or not tool.function.name
    ):
        raise ValueError(f"Could not find function '{function_name}'")

    arguments = json.loads(function_arguments_json)
    logger.debug_kv(
        f"{tool.function.name}", f"called with arguments: {arguments}", "green"
    )
    output = tool.function.python_fn(**arguments)
    if inspect.isawaitable(output):
        output = run_sync(output)
    truncated_output = str(output)[:100]
    if len(truncated_output) < len(str(output)):
        truncated_output += "..."
    logger.debug_kv(f"{tool.function.name}", f"returned: {truncated_output}", "green")
    if not isinstance(output, str):
        output = json.dumps(output)
    return output
