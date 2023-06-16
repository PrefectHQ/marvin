import json
from logging import Logger
from typing import TYPE_CHECKING, Any, Union

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
        logger.debug(f"Sending messages to LLM:' {messages}")

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
            logger.debug(
                f"Running tool '{function_payload['name']}' with payload"
                f" {function_payload['arguments']}"
            )
            tool_name = function_payload["name"]
            tool = next((t for t in tools if t.name == tool_name), None)
            if not tool:
                break
            try:
                tool_output = tool.run(**json.loads(function_payload["arguments"]))
            except Exception as exc:
                tool_output = str(exc)

            if tool.is_final:
                return tool_output
            else:
                messages.append(
                    Message(
                        role="function", name=tool_name, content=str(tool_output or "")
                    )
                )
            i += 1

        else:
            break

    return response
