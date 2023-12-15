"""Module for NLI tool utilities."""
import inspect
import json

from marvin.requests import Tool
from marvin.utilities.asyncio import run_sync
from marvin.utilities.logging import get_logger
from marvin.utilities.pydantic import cast_callable_to_model

logger = get_logger("Tools")


def tool_from_function(fn: callable, name: str = None, description: str = None):
    model = cast_callable_to_model(fn)
    return Tool(
        type="function",
        function=dict(
            name=name or fn.__name__,
            description=description or fn.__doc__,
            # use deprecated schema because this is based on a pydantic v1
            # validate_arguments
            parameters=model.model_json_schema(),
            python_fn=fn,
        ),
    )


def call_function_tool(
    tools: list[Tool], function_name: str, function_arguments_json: str
):
    tool = next(
        (
            tool
            for tool in tools
            if isinstance(tool, Tool)
            and tool.function
            and tool.function.name == function_name
        ),
        None,
    )
    if not tool:
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
