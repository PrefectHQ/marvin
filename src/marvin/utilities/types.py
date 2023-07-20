import inspect
import logging
from types import GenericAlias
from typing import Any, Callable, _SpecialForm

import pydantic
from pydantic import BaseModel, PrivateAttr

from marvin.utilities.logging import get_logger


class MarvinBaseModel(BaseModel):
    class Config:
        extra = "forbid"


class LoggerMixin(BaseModel):
    """
    BaseModel mixin that adds a private `logger` attribute
    """

    _logger: logging.Logger = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._logger = get_logger(type(self).__name__)

    @property
    def logger(self):
        return self._logger


def function_to_model(
    function: Callable[..., Any], name: str = None, description: str = None
) -> dict:
    """
    Converts a function's arguments into an OpenAPI schema by parsing it into a
    Pydantic model. To work, all arguments must have valid type annotations.
    """
    signature = inspect.signature(function)

    fields = {
        p: (
            signature.parameters[p].annotation,
            (
                signature.parameters[p].default
                if signature.parameters[p].default != inspect._empty
                else ...
            ),
        )
        for p in signature.parameters
        if p != getattr(function, "__self__", None)
    }

    # Create Pydantic model
    try:
        Model = pydantic.create_model(name or function.__name__, **fields)
    except RuntimeError as exc:
        if "see `arbitrary_types_allowed` " in str(exc):
            raise ValueError(
                f"Error while inspecting {function.__name__} with signature"
                f" {signature}: {exc}"
            )
        else:
            raise

    return Model


def function_to_schema(function: Callable[..., Any], name: str = None) -> dict:
    """
    Converts a function's arguments into an OpenAPI schema by parsing it into a
    Pydantic model. To work, all arguments must have valid type annotations.
    """
    Model = function_to_model(function, name=name)

    return Model.schema()


def safe_issubclass(type_, classes):
    if isinstance(type_, type) and not isinstance(type_, GenericAlias):
        return issubclass(type_, classes)
    else:
        return False


def type_to_schema(type_, set_root_type: bool = True) -> dict:
    if safe_issubclass(type_, pydantic.BaseModel):
        schema = type_.schema()
        # if the docstring was updated at runtime, make it the description
        if type_.__doc__ and type_.__doc__ != schema.get("description"):
            schema["description"] = type_.__doc__
        return schema

    elif set_root_type:

        class Model(pydantic.BaseModel):
            __root__: type_

        return Model.schema()
    else:

        class Model(pydantic.BaseModel):
            data: type_

        return Model.schema()


def genericalias_contains(genericalias, target_type):
    """
    Explore whether a type or generic alias contains a target type. The target
    types can be a single type or a tuple of types.

    Useful for seeing if a type contains a pydantic model, for example.
    """
    if isinstance(target_type, tuple):
        return any(genericalias_contains(genericalias, t) for t in target_type)

    if isinstance(genericalias, GenericAlias):
        if safe_issubclass(genericalias.__origin__, target_type):
            return True
        for arg in genericalias.__args__:
            if genericalias_contains(arg, target_type):
                return True
    elif isinstance(genericalias, _SpecialForm):
        return False
    else:
        return safe_issubclass(genericalias, target_type)

    return False
