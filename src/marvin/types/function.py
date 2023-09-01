import copy
import inspect
import re
from functools import partial
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel, validate_arguments
from pydantic.decorator import (
    ALT_V_ARGS,
    ALT_V_KWARGS,
    V_DUPLICATE_KWARGS,
    V_POSITIONAL_ONLY_NAME,
)

extraneous_fields = [
    "args",
    "kwargs",
    ALT_V_ARGS,
    ALT_V_KWARGS,
    V_POSITIONAL_ONLY_NAME,
    V_DUPLICATE_KWARGS,
]


def openai_schema(
    schema: Callable[[BaseModel], dict[str, Any]],
) -> Callable[[], dict[str, Any]]:
    if schema().get("name"):
        return schema

    def wrapped_schema():
        response: dict[str, Any] = {"parameters": copy.deepcopy(schema())}
        response["name"] = response["parameters"].pop("title", "format_response")
        response["description"] = response["parameters"].get("description", "")
        # Hack to order the parameters.
        response["parameters"] = response.pop("parameters")

        return response

    return wrapped_schema


def get_openai_function_schema(schema, model):
    # Make a copy of the schema.
    _schema = copy.deepcopy(schema)

    # Prune the schema of 'titles'.
    _schema.pop("title", None)
    for key, value in schema["properties"].items():
        if key in extraneous_fields:
            _schema["properties"].pop(key, None)
        else:
            _schema["properties"][key].pop("title", None)

    # Clear the existing schema.
    schema.clear()

    # Reconstruct the schema.
    schema["name"] = getattr(model, "name", model.Config.fn.__name__)
    schema["description"] = getattr(model, "description", model.Config.fn.__doc__)
    schema["parameters"] = {
        k: v for (k, v) in _schema.items() if k not in extraneous_fields
    }
    return schema


class FunctionConfig(BaseModel):
    fn: Callable
    name: str
    description: str = ""
    schema_extra: Optional[Callable] = get_openai_function_schema

    def __init__(self, fn, **kwargs):
        kwargs.setdefault("name", fn.__name__ or "")
        kwargs.setdefault("description", fn.__doc__ or "")
        super().__init__(fn=fn, **kwargs)

    def getsource(self):
        try:
            return re.search("def.*", inspect.getsource(self.fn), re.DOTALL).group()
        except Exception:
            return None

    def bind_arguments(self, *args, **kwargs):
        bound_arguments = inspect.signature(self.fn).bind(*args, **kwargs)
        bound_arguments.apply_defaults()
        return bound_arguments.arguments

    def response_model(self, *args, **kwargs):
        def format_response(data: inspect.signature(self.fn).return_annotation):
            """Function to format the final response to the user"""
            return None

        format_response.__name__ = kwargs.get("name", format_response.__name__)
        format_response.__doc__ = kwargs.get("description", format_response.__doc__)
        response_model = Function(format_response).model
        response_model.__name__ = format_response.__name__
        response_model.__doc__ = format_response.__doc__
        response_model.__signature__ = inspect.signature(format_response)
        return response_model


class Function:
    """
    A wrapper class to add additional functionality to a function,
    such as a schema, response model, and more.
    """

    def __new__(cls, fn: Callable, **kwargs):
        config = FunctionConfig(fn, **kwargs)

        if hasattr(fn, "schema"):
            instance = fn

        else:
            instance = validate_arguments(fn, config=config.dict())
            instance.schema = instance.model.schema
        instance.evaluate_raw = partial(cls.evaluate_raw, fn=instance)

        instance.response_model = config.response_model
        instance.bind_arguments = config.bind_arguments
        instance.getsource = config.getsource

        instance.__name__ = config.name
        instance.__doc__ = config.description
        return instance

    @classmethod
    def from_model(
        cls,
        model: Type[BaseModel],
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs,
    ):
        model.__signature__ = inspect.Signature(
            list(model.__signature__.parameters.values()), return_annotation=model
        )

        instance = cls.__new__(
            cls,
            model,
            **{
                "name": name or model.__name__,
                "description": description or model.__doc__,
                **kwargs,
            },
        )

        instance.schema = openai_schema(model.schema)

        return instance

    @classmethod
    def from_return_annotation(
        cls, fn: Callable, *args, name: str = None, description: str = None
    ):
        def format_final_response(data: inspect.signature(fn).return_annotation):
            """Function to format the final response to the user"""
            return None

        format_final_response.__name__ = name or format_final_response.__name__
        format_final_response.__doc__ = description or format_final_response.__doc__
        response_model = cls(format_final_response)
        return response_model

    @classmethod
    def evaluate_raw(cls, args: str, /, *, fn: Callable, **kwargs):
        return fn(**fn.model.parse_raw(args).dict(exclude_none=True))


class FunctionRegistry(list[Function]):
    def schema(self, *args, **kwargs):
        return [fn.schema(*args, **kwargs) for fn in self]
