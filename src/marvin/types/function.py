import copy
from typing import Callable, Optional, Type

from pydantic import BaseModel
from pydantic.decorator import (
    ALT_V_ARGS,
    ALT_V_KWARGS,
    V_DUPLICATE_KWARGS,
    V_POSITIONAL_ONLY_NAME,
)

from marvin.utilities.types import function_to_model

extraneous_fields = [
    "args",
    "kwargs",
    ALT_V_ARGS,
    ALT_V_KWARGS,
    V_POSITIONAL_ONLY_NAME,
    V_DUPLICATE_KWARGS,
]


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


class FunctionConfig(BaseModel):
    fn: Callable
    name: str
    description: str = ""
    schema_extra: Optional[Callable] = get_openai_function_schema

    def __init__(self, fn, **kwargs):
        kwargs.setdefault("name", fn.__name__ or "")
        kwargs.setdefault("description", fn.__doc__ or "")
        super().__init__(fn=fn, **kwargs)


class Function:
    def __init__(self, fn: Callable, **kwargs):
        self.fn = fn
        self.name = kwargs.get("name", fn.__name__)
        self.description = kwargs.get("description", fn.__doc__ or "")
        self.model = function_to_model(self.fn)
        self.schema = self.model.schema()
        self.signature = self.model.__signature__

    def evaluate_raw(self, args: str, **kwargs):
        validated_args = self.fn.model.parse_raw(args)
        return self.fn(**validated_args.dict(exclude_none=True))

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    @classmethod
    def from_model(cls, model: Type[BaseModel], **kwargs):
        instance = cls.__new__(
            cls,
            model,
            **{
                "name": "format_response",
                "description": "Format the response",
                **kwargs,
            },
        )
        instance.__signature__ = model.__signature__
        return instance
