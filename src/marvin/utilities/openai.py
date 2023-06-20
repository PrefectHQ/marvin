import json
from logging import Logger
from typing import TYPE_CHECKING, Any, Callable, Union

from langchain.schema import AIMessage

import marvin
import marvin.utilities.llms
from marvin.models.threads import Message
from marvin.utilities.logging import get_logger

if TYPE_CHECKING:
    from marvin.openai.tools import Tool


async def call_llm_with_tools(
    llm,
    messages: list[Message],
    logger: Logger = None,
    tools: list["Tool"] = None,
    function_call="auto",
    message_processor: Callable[[list[Message]], list[Message]] = None,
    **kwargs,
) -> Union[AIMessage, Any]:
    """
    Calls a compatible OpenAI LLM with a list of messages and a list of tools.
    Uses the `functions` API to generate tool inputs and loops until the LLM
    stops calling functions.

    function_call: 'auto' (automatically decide whether to call a function),
        'none' (do not call a function) or {'name': <a function name>} to call a
        specific function.
    """

    if logger is None:
        logger = get_logger("llm")

    messages = messages.copy()

    if not llm.model_name.endswith("-0613"):
        raise ValueError("Tools are only compatible with the latest OpenAI models.")

    functions = [t.as_function_schema() for t in tools]

    i = 1
    while i <= marvin.settings.llm_max_tool_iterations:
        response = await marvin.utilities.llms.call_llm_messages(
            llm,
            messages,
            logger,
            functions=functions,
            # force no function call if we're at  max iterations
            function_call=(
                function_call if i < marvin.settings.llm_max_tool_iterations else "none"
            ),
            **kwargs,
        )

        if function_payload := response.additional_kwargs.get("function_call", None):
            tool_name = function_payload["name"]
            tool = next((t for t in tools if t.name == tool_name), None)
            if not tool:
                break
            try:
                logger.debug(
                    f"Running tool '{function_payload['name']}' with payload"
                    f" {function_payload['arguments']}"
                )
                arguments = json.loads(function_payload["arguments"])
                if not isinstance(arguments, dict):
                    raise ValueError(
                        "Expected a dictionary of arguments, got a"
                        f" {type(arguments).__name__}. Try calling the function again"
                        " using the correct keyword names."
                    )
                tool_output = tool.run(**arguments)
                if tool.is_final:
                    return tool_output
            except Exception as exc:
                logger.error(
                    f'The function "{tool_name}" encountered an error. The payload'
                    f' was {function_payload["arguments"]}\n\n{str(exc)}'
                )
                tool_output = (
                    f"The function encountered an error: {str(exc)}\n\nThe payload you"
                    f" provided was: '{function_payload['arguments']}\n\nPlease try"
                    " calling the function again.'"
                )

            messages.append(
                Message(role="function", name=tool_name, content=str(tool_output or ""))
            )
            i += 1

            # optionally process messages
            if message_processor:
                messages = message_processor(messages)

        else:
            break

    return response
