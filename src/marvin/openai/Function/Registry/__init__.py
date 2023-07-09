from typing import Any, Callable, Dict, List, Optional, Set, Type, Union
from fastapi.routing import APIRouter
from pydantic import BaseModel, validate_arguments
from marvin.utilities.types import function_to_model
from marvin.models.messages import Message
from marvin.openai.Function import marvin_fn, openai_fn
from openai.openai_object import OpenAIObject


class FunctionRegistry(APIRouter):
    def __init__(self, function_decorator=marvin_fn, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.function_decorator = function_decorator

    @property
    def endpoints(self):
        return [route.endpoint for route in self.routes]

    @property
    def schema(self):
        return [fn.schema() for fn in self.endpoints]

    @property
    def functions(self):
        return [fn.schema() for fn in self.endpoints]

    def include(self, registry: "FunctionRegistry", *args, **kwargs):
        super().include_router(registry, *args, **kwargs)
        # Add some 50-IQ idempotency.
        self.routes = list({x.name: x for x in self.routes}.values())

    def register(self, fn: Optional[Callable] = None, **kwargs: Any) -> Callable:
        def decorator(fn: Callable, *args) -> Callable:
            fn = self.function_decorator(fn=fn, **kwargs)
            self.add_api_route(
                **{
                    **{
                        "name": fn.name,
                        "path": f"/{fn.name}",
                        "endpoint": fn,
                        "description": fn.description,
                        "methods": ["POST"],
                    },
                    **kwargs,
                }
            )
            return fn

        if fn:
            # if the decorator was called with parentheses
            return decorator(fn)
        else:
            # else, return the decorator to be called later
            return decorator


class OpenAIFunctionRegistry(FunctionRegistry):
    def __init__(self, *args, **kwargs):
        super().__init__(function_decorator=openai_fn, *args, **kwargs)

    def from_openai_response(self, response: OpenAIObject) -> Any:
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
        return {fn.name: fn.from_openai_response(response) for fn in self.endpoints}
