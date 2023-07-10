from typing import Any, Callable, Dict, List, Union, TypeVar, Type
from marvin.utilities.types import function_to_model
from openai.openai_object import OpenAIObject
import functools
import json
from pydantic import validate_arguments


T = TypeVar("T")
A = TypeVar("A")


class Function:
    def __init__(
        self, *, fn: Callable[[A], T] = None, name: str = None, description: str = None
    ) -> None:
        self.fn = fn
        self.name = name or self.fn.__name__
        self.description = description or self.fn.__doc__

        super().__init__()

    @property
    def model(self):
        return function_to_model(self.fn, name=self.name, description=self.description)

    def schema(self, *args, name: str = None, description: str = None, **kwargs):
        schema = self.model.schema(*args, **kwargs)
        return {
            "name": name or schema.pop("title"),
            "description": description or self.fn.__doc__,
            "parameters": schema,
        }


class OpenAIFunction(Function):
    def __call__(self, response: OpenAIObject) -> T:
        return self.from_openai_response(response)

    @validate_arguments
    def from_openai_response(self, response: OpenAIObject) -> T:
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


def FunctionDecoratorFactory(
    name: str = "marvin", func_class: Type[T] = None
) -> Callable[[A], T]:
    def decorator(fn: Callable[[A], T] = None) -> Callable[[A], T]:
        if fn is None:
            return functools.partial(decorator)
        else:
            instance = func_class(fn=fn)
            setattr(fn, name, instance)
            for method in dir(instance):
                is_method_private = method.startswith("__")
                if not is_method_private:
                    setattr(fn, method, getattr(instance, method))
        return fn

    return decorator


marvin_fn = FunctionDecoratorFactory(name="marvin", func_class=Function)
openai_fn = FunctionDecoratorFactory(name="openai", func_class=OpenAIFunction)
