import inspect
import json
from logging import Logger
from typing import Any, Callable, Union

import openai
import openai.openai_object
from pydantic import BaseModel, Field, validator

import marvin
import marvin.utilities.types
from marvin.models.messages import Message, Role
from marvin.utilities.logging import get_logger


class OpenAIFunction(BaseModel):
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


class ChatLLM(BaseModel):
    name: str = None
    model: str = Field(default=marvin.settings.llm_model)
    max_tokens: int = Field(default=marvin.settings.llm_max_tokens)
    temperature: float = Field(default=marvin.settings.llm_temperature)
    stream: bool = Field(default=False)

    @validator("name", always=True)
    def default_name(cls, v):
        if v is None:
            v = cls.__name__
        return v

    async def run(
        self,
        messages: list[Message],
        *,
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
        elif function_call not in (
            ["auto", "none"] + [{"name": f.name} for f in functions]
        ):
            raise ValueError(f"Invalid function_call value: {function_call}")
        if logger is None:
            logger = get_logger(self.name)

        # ----------------------------------
        # Form OpenAI-specific arguments
        # ----------------------------------

        openai_messages = [m.as_chat_message() for m in messages]
        openai_functions = [
            f.dict(exclude={"fn"}, exclude_none=True) for f in functions
        ]

        # only add to kwargs if supplied, because empty parameters are not
        # allowed by OpenAI
        if functions:
            kwargs["functions"] = openai_functions
            kwargs["function_call"] = function_call

        # ----------------------------------
        # Call OpenAI LLM
        # ----------------------------------

        response: openai.openai_object.OpenAIObject = (
            await openai.ChatCompletion.acreate(
                api_key=marvin.settings.openai_api_key.get_secret_value(),
                model=self.model,
                messages=openai_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs,
            )
        )

        msg = response.choices[0].message.to_dict_recursive()
        if msg["role"] == "assistant":
            # ----------------------------------
            # Call functions if requested
            # ----------------------------------

            if fn_call := msg.get("function_call"):
                fn_name = fn_call.get("name")
                fn_args = json.loads(fn_call.get("arguments", "{}"))
                try:
                    # retrieve the named function
                    openai_fn = next((f for f in functions if f.name == fn_name), None)
                    if openai_fn is None:
                        raise ValueError(f'Function "{fn_call["name"]}" not found.')

                    if not isinstance(fn_args, dict):
                        raise ValueError(
                            "Expected a dictionary of arguments, got a"
                            f" {type(fn_args).__name__}."
                        )

                    # call the function
                    if openai_fn.fn is not None:
                        logger.debug(
                            f"Running function '{openai_fn.name}' with payload"
                            f" {fn_args}"
                        )
                        fn_result = openai_fn.fn(**fn_args)
                        if inspect.isawaitable(fn_result):
                            fn_result = await fn_result

                    # if the function is undefined, return the arguments as its output
                    else:
                        fn_result = fn_args
                    logger.debug(f"Result of function '{openai_fn.name}': {fn_result}")

                except Exception as exc:
                    fn_result = (
                        f"The function '{fn_name}' encountered an error:"
                        f" {str(exc)}\n\nThe payload you provided was: {fn_args}\n\nYou"
                        " can try to fix the error and call the function again.'"
                    )
                    logger.error(fn_result)

                response = Message(
                    role=Role.FUNCTION,
                    name=fn_name,
                    content=str(fn_result),
                    data=dict(name=fn_name, arguments=fn_args, result=fn_result),
                )

            # ----------------------------------
            # Otherwise return AI response
            # ----------------------------------

            else:
                response = Message(role=Role.ASSISTANT, content=msg["content"])

        return response