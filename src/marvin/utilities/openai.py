import inspect
import json
from logging import Logger
from typing import TYPE_CHECKING, Any, Callable, Union

import openai

import marvin
import marvin.utilities.llms
from marvin.models.threads import Message
from marvin.utilities.logging import get_logger
from marvin.utilities.types import MarvinBaseModel

if TYPE_CHECKING:
    pass


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
    fn: Callable = None

    @classmethod
    def from_function(cls, fn: Callable, **kwargs):
        return cls(
            name=kwargs.get("name", fn.__name__),
            description=kwargs.get("description", fn.__doc__),
            parameters=marvin.utilities.types.function_to_schema(fn),
            function=fn,
        )


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
) -> Message:
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
        api_key=marvin.settings.openai_api_key.get_secret_value(),
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
        # ----------------------------------
        # Call functions
        # ----------------------------------
        if fn_call := msg.get("function_call"):
            fn_name = fn_call.get("name")
            fn_args = json.loads(fn_call.get("arguments", "{}"))
            try:
                # retrieve the function
                function = next((f for f in functions if f.name == fn_name), None)
                if function is None:
                    raise ValueError(f'Function "{fn_call["name"]}" not found.')

                if not isinstance(fn_args, dict):
                    raise ValueError(
                        "Expected a dictionary of arguments, got a"
                        f" {type(fn_args).__name__}."
                    )

                # call the function
                if function.fn is not None:
                    logger.debug(
                        f"Running function '{function.name}' with payload {fn_args}"
                    )
                    fn_result = function.fn(**fn_args)
                    if inspect.isawaitable(fn_result):
                        fn_result = await fn_result

                # if the function is undefined, return the arguments as its output
                else:
                    fn_result = fn_args
                logger.debug(f"Result of function '{function.name}': {fn_result}")

            except Exception as exc:
                fn_result = (
                    f"The function '{fn_name}' encountered an error:"
                    f" {str(exc)}\n\nThe payload you provided was:"
                    f" {fn_args}\n\nYou can try to fix the error and call the function"
                    " again.'"
                )
                logger.error(fn_result)

            response = Message(
                role="function",
                name=fn_name,
                content=str(fn_result),
                data=dict(arguments=fn_args, result=fn_result),
            )

        else:
            response = Message(role="ai", content=msg["content"])
    return response
