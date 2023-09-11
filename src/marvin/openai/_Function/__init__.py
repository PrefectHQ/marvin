import json
from typing import TypeVar
from openai.openai_object import OpenAIObject

from pydantic import validate_arguments
from marvin.functions import Function, FunctionDecoratorFactory


T = TypeVar("T")
A = TypeVar("A")


class OpenAIFunction(Function):
    def __call__(self, response: OpenAIObject) -> T:
        return self.from_response(response)

    @validate_arguments
    def from_response(self, response: OpenAIObject) -> T:
        relevant_calls = [
            choice.message.function_call
            for choice in response.choices
            if hasattr(choice.message, "function_call")
            and self.name == choice.message.function_call.get("name", None)
        ]

        arguments = [
            json.loads(function_call.get("arguments"))
            for function_call in relevant_calls
        ]

        responses = [self.fn(**argument) for argument in arguments]

        if len(responses) == 0:
            return None
        elif len(responses) == 1:
            return responses[0]
        else:
            return responses


openai_fn = FunctionDecoratorFactory(name="openai", func_class=OpenAIFunction)
