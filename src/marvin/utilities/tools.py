import json

from marvin.requests import FunctionTool, Tool
from marvin.utilities.logging import get_logger

logger = get_logger("Tools")


def call_function(tools: list[Tool], function_name: str, function_arguments_json: str):
    tool = next(
        (
            tool
            for tool in tools
            if isinstance(tool, FunctionTool) and tool.function.name == function_name
        ),
        None,
    )
    if not tool:
        raise ValueError(f"Could not find function '{function_name}'")

    arguments = json.loads(function_arguments_json)
    logger.debug("Calling {tool.function.name} with arguments: {arguments}")
    output = tool.function.python_fn(**arguments)
    logger.debug(f"{tool.function.name} returned: {output}")
    return output
