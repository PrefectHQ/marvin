import inspect
import json
from ast import literal_eval
from typing import Callable, List, Optional, Union

from pydantic import Field, root_validator, validator

import marvin
from marvin.engine.language_models import OpenAIFunction
from marvin.utilities.messages import Message, Role

from .base import Executor


class OpenAIFunctionsExecutor(Executor):
    """
    An executor that understands how to pass functions to the LLM, interpret
    responses that request function calls, and iteratively continue to process
    functions until the LLM responds directly to the user. This uses the OpenAI
    Functions API, so provider LLMs must be compatible.
    """

    functions: List[OpenAIFunction] = Field(default=None)
    function_call: Union[str, dict[str, str]] = Field(default=None)
    max_iterations: Optional[int] = Field(
        default_factory=lambda: marvin.settings.ai_application_max_iterations
    )
    stream_handler: Callable[[Message], None] = Field(default=None)

    @validator("functions", pre=True)
    def validate_functions(cls, v):
        if v is None:
            return None
        v = [
            OpenAIFunction.from_function(i) if not isinstance(i, OpenAIFunction) else i
            for i in v
        ]
        return v

    @root_validator
    def validate_function_call(cls, values):
        # validate function call
        if values["functions"] and values.get("function_call") is None:
            values["function_call"] = "auto"
        elif values["function_call"] not in (
            ["auto", "none"] + [{"name": f.name} for f in values["functions"]]
        ):
            raise ValueError(f'Invalid function_call: {values["function_call"]}')

        return values

    async def run_engine(self, messages: list[Message]) -> Message:
        """
        Implements one step of the LLM loop
        """

        kwargs = {}

        if self.functions:
            kwargs["functions"] = self.functions
            kwargs["function_call"] = self.function_call

        llm_response = await self.model.run(
            messages=messages,
            stream_handler=self.stream_handler,
            **kwargs,
        )
        return llm_response

    async def stop_condition(
        self, messages: List[Message], responses: List[Message]
    ) -> bool:
        # if the number of responses exceeds max iterations, stop

        if self.max_iterations is not None and len(responses) >= self.max_iterations:
            return True

        # if function calls are set to auto and the most recent call was a
        # function, continue
        if self.function_call == "auto":
            if responses and responses[-1].role == Role.FUNCTION_RESPONSE:
                return False

        # if a specific function call was requested but errored, continue
        elif self.function_call != "none":
            if responses and responses[-1].data.get("is_error"):
                return False

        # otherwise stop
        return True

    async def process_response(self, response: Message) -> Message:
        if response.role == Role.FUNCTION_REQUEST:
            return await self.process_function_call(response)
        else:
            return response

    async def process_function_call(self, response: Message) -> Message:
        response_data = {}

        function_call = response.data["function_call"]
        fn_name = function_call.get("name")
        fn_args = function_call.get("arguments")
        response_data["name"] = fn_name
        try:
            try:
                fn_args = json.loads(function_call.get("arguments", "{}"))
            except json.JSONDecodeError:
                fn_args = literal_eval(function_call.get("arguments", "{}"))
            response_data["arguments"] = fn_args

            # retrieve the named function
            openai_fn = next((f for f in self.functions if f.name == fn_name), None)
            if openai_fn is None:
                raise ValueError(f'Function "{function_call["name"]}" not found.')

            if not isinstance(fn_args, dict):
                raise ValueError(
                    "Expected a dictionary of arguments, got a"
                    f" {type(fn_args).__name__}."
                )

            # call the function
            if openai_fn.fn is not None:
                self.logger.debug(
                    f"Running function '{openai_fn.name}' with payload {fn_args}"
                )
                fn_result = openai_fn.fn(**fn_args)
                if inspect.isawaitable(fn_result):
                    fn_result = await fn_result

            # if the function is undefined, return the arguments as its output
            else:
                fn_result = fn_args
            self.logger.debug(f"Result of function '{openai_fn.name}': {fn_result}")
            response_data["is_error"] = False

        except Exception as exc:
            fn_result = (
                f"The function '{fn_name}' encountered an error:"
                f" {str(exc)}\n\nThe payload you provided was: {fn_args}\n\nYou"
                " can try to fix the error and call the function again."
            )
            self.logger.debug_kv("Error", fn_result, key_style="red")
            response_data["is_error"] = True

        response_data["result"] = fn_result

        return Message(
            role=Role.FUNCTION_RESPONSE,
            name=fn_name,
            content=str(fn_result),
            data=response_data,
            llm_response=response.llm_response,
        )
