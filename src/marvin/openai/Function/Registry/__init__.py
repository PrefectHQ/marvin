from typing import Any, Callable, Dict, List, Optional, Set, Type, Union
from fastapi.routing import APIRouter
from pydantic import BaseModel, validate_arguments
from marvin.utilities.types import function_to_model
from marvin.utilities.messages import Message
from marvin.openai.Function import openai_fn
from openai.openai_object import OpenAIObject
from marvin.functions import FunctionRegistry


class OpenAIFunctionRegistry(FunctionRegistry):
    def __init__(self, function_decorator=openai_fn, *args, **kwargs):
        self.function_decorator = function_decorator
        super().__init__(function_decorator=function_decorator, *args, **kwargs)

    def from_response(self, response: OpenAIObject) -> Any:
        return next(
            iter(
                [
                    {"name": k, "content": v}
                    for k, v in self.dict_from_openai_response(response).items()
                    if v is not None
                ]
            ),
            None,
        )

    def dict_from_openai_response(self, response: OpenAIObject) -> Any:
        return {
            fn.name: fn.from_response(response)
            for fn in map(lambda fn: self.function_decorator(fn=fn), self.endpoints)
        }
