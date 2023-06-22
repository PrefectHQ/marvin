import inspect
import json
import math
from logging import Logger
from typing import TYPE_CHECKING, Any, Callable, Union

import openai
from langchain.schema import AIMessage

import marvin
import marvin.utilities.llms
from marvin.models.threads import Message
from marvin.utilities.logging import get_logger
from marvin.utilities.types import MarvinBaseModel

if TYPE_CHECKING:
    from marvin.openai.tools import Tool


def prepare_messages(messages: list[Message]) -> list[dict[str, Any]]:
    openai_messages = []
    for msg in messages:
        if msg.role == "system":
            openai_messages.append({"role": "system", "content": msg.content})
        elif msg.role == "ai":
            openai_messages.append({"role": "assistant", "content": msg.content})
        elif msg.role == "user":
            openai_messages.append({"role": "user", "content": msg.content})
        elif msg.role == "function":
            openai_messages.append(
                {"role": "function", "name": msg.name, "content": msg.content}
            )
        else:
            raise ValueError(f"Unrecognized role: {msg.role}")
    return openai_messages


class OpenAIFunction(MarvinBaseModel):
    name: str
    description: str = None
    parameters: dict[str, Any] = {"type": "object", "properties": {}}
    function: Callable = None

    @classmethod
    def from_function(cls, fn: Callable, **kwargs):
        return cls(
            name=kwargs.get("name", fn.__name__),
            description=kwargs.get("description", fn.__doc__),
            parameters=marvin.utilities.types.function_to_schema(fn),
            function=fn,
        )


class OpenAIFunctionCall(MarvinBaseModel):
    name: str
    arguments: dict[str, Any]
    function: OpenAIFunction


async def call_llm_chat(
    messages: list[Message],
    *,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    functions: list[OpenAIFunction] = None,
    function_call: Union[str, dict[str, str]] = None,
    logger: Logger = None,
    **kwargs,
) -> Union[Message, OpenAIFunctionCall]:
    """Calls an OpenAI LLM with a list of messages and returns the response."""

    # ----------------------------------
    # Validate arguments
    # ----------------------------------

    if functions is None:
        functions = []
    if function_call is None:
        function_call = "auto"
    elif function_call not in [
        "auto",
        "none",
        *[{"name": f.name for f in functions or []}],
    ]:
        raise ValueError(f"Invalid function_call value: {function_call}")
    if model is None:
        model = marvin.settings.llm_model
    if temperature is None:
        temperature = marvin.settings.llm_temperature
    if max_tokens is None:
        max_tokens = marvin.settings.llm_max_tokens
    if logger is None:
        logger = get_logger("llm")

    # ----------------------------------
    # Form OpenAI-specific arguments
    # ----------------------------------

    openai_messages = prepare_messages(messages)
    openai_functions = [
        f.dict(include={"name", "description", "parameters"}, exclude_none=True)
        for f in functions
    ]

    # add separately because empty parameters are not allowed
    if functions:
        kwargs["functions"] = openai_functions
        kwargs["function_call"] = function_call

    # ----------------------------------
    # Call OpenAI LLM
    # ----------------------------------

    response: openai.openai_object.OpenAIObject = await openai.ChatCompletion.acreate(
        model=model,
        messages=openai_messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
    # ----------------------------------
    # Format response
    # ----------------------------------

    msg = response.choices[0].message.to_dict_recursive()
    if msg["role"] == "assistant":
        if fn_call := msg.get("function_call"):
            try:
                # retrieve the function
                function = next(f for f in functions if f.name == fn_call["name"])
                arguments = json.loads(fn_call["arguments"])

                if not isinstance(arguments, dict):
                    raise ValueError(
                        "Expected a dictionary of arguments, got a"
                        f" {type(arguments).__name__}. Try calling the function again"
                        " using the correct keyword names."
                    )

                # call the function
                if function.function is not None:
                    logger.debug(
                        f"Running function '{function.name}' with payload {arguments}"
                    )
                    fn_result = function.function(**arguments)
                    if inspect.isawaitable(fn_result):
                        fn_result = await fn_result

                # if the function is undefined, return the arguments as its output
                else:
                    fn_result = arguments
                logger.debug(f"Result of function '{function.name}': {fn_result}")

            except Exception as exc:
                logger.error(exc)
                fn_result = (
                    f"The function '{function.name}' encountered an error:"
                    f" {str(exc)}\n\nThe payload you provided was: {arguments}\n\nYou"
                    " can try calling the function again.'"
                )

            response = Message(
                role="function",
                name=function.name,
                content=str(fn_result),
                data=dict(arguments=arguments, result=fn_result),
            )
        else:
            response = Message(role="ai", content=msg["content"])
    return response


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

    if (max_iterations := marvin.settings.llm_max_tool_iterations) is None:
        max_iterations = math.inf

    i = 1
    while i <= max_iterations:
        response = openai.ChatCompletion.create

        response = await marvin.utilities.llms.call_llm_messages(
            llm,
            messages,
            logger,
            functions=functions,
            # force no function call if we're at  max iterations
            function_call=(function_call if i < max_iterations else "none"),
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
                logger.debug(
                    f"Received output from tool '{function_payload['name']}':"
                    f" {tool_output}"
                )
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
